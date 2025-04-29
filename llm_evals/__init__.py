from os.path import dirname
import click
import llm
import pathlib
import sqlite_utils
import json
import csv
import yaml


from llm.cli import logs_db_path
from llm.plugins import pm

from llm_evals.models import Eval
from llm_evals.parsers import parse_eval
from . import hookspecs
from . import checks
from .migrations import migrate

pm.add_hookspecs(hookspecs)


@llm.hookimpl
def register_commands(cli):
    @cli.group()
    def evals():
        pass

    @evals.command()
    @click.argument("evals", nargs=-1, required=True, type=click.Path(exists=True))
    @click.option(
        "-d",
        "--database",
        type=click.Path(readable=True, dir_okay=False),
        help="Path to evals database",
    )
    def run(evals, database):
        "Run evals against models"
        log_path = pathlib.Path(database) if database else logs_db_path()
        (log_path.parent).mkdir(parents=True, exist_ok=True)
        db = sqlite_utils.Database(log_path)
        migrate(db)

        checks = []
        for check in pm.hook.register_eval_checks():
            checks.extend(check)

        for eval_path in evals:
            with open(eval_path) as f:
                base_dir = dirname(eval_path)
                eval_ = parse_eval(yaml.safe_load(f), base_dir)

            missing_results = get_missing_results(db, eval_)
            click.echo(f"Found {len(missing_results)} combinations without results yet")
            i = 0
            for combination in missing_results:
                i += 1
                click.echo(f"Running combination {i} of {len(missing_results)}")
                (response_id, result) = run_eval(db, combination, checks)
                click.echo(f"Result: {result}")
                store_result(db, combination, response_id, result)

            results = get_eval_results(db, eval_)
            if len(results):
                with open("./results.csv", "w") as f:
                    writer = csv.DictWriter(f, results[0].keys())
                    writer.writeheader()
                    writer.writerows(results)
                    click.echo("Results written to results.csv")
            else:
                click.echo("No results")

            aggregates = calculate_aggregates(eval_, results)
            if len(aggregates):
                with open("./aggregates.csv", "w") as f:
                    writer = csv.DictWriter(f, aggregates[0].keys())
                    writer.writeheader()
                    writer.writerows(aggregates)
                    click.echo("Aggregates written to aggregates.csv")
            else:
                click.echo("No aggregates")

            for agg in aggregates:
                click.echo("-" * 50)
                click.echo(f"Model: {agg['model']}")
                click.echo(f"Prompt: {agg['prompt_json'][:50]}...")
                click.echo(f"Total checks: {agg['total_checks']}")
                click.echo(f"Correct checks: {agg['correct_checks']}")
                click.echo(f"Accuracy: {agg['accuracy']:.2%}")
            click.echo("-" * 50)


def store_result(db, combination, response_id, result):
    existing_results = list(
        db["evals_checks_results"].rows_where(
            "task_id = :task_id AND model_id = :model_id AND prompt_id = :prompt_id AND case_id = :case_id AND check_id = :check_id AND response_id = :response_id",
            [
                combination["task_id"],
                combination["model_id"],
                combination["prompt_id"],
                combination["case_id"],
                combination["check_id"],
                response_id,
            ],
        )
    )

    if existing_results:
        result_id = existing_results[0]["id"]
        db["evals_checks_results"].update(result_id, {"result": result})
    else:
        db["evals_checks_results"].insert(
            {
                "task_id": combination["task_id"],
                "model_id": combination["model_id"],
                "prompt_id": combination["prompt_id"],
                "case_id": combination["case_id"],
                "check_id": combination["check_id"],
                "response_id": response_id,
                "result": result,
            }
        )


def get_missing_results(db, eval_: Eval):
    task_id = db["evals_tasks"].lookup({"name": eval_.name})
    missing_results = []

    for model in eval_.models:
        model_id = db["evals_models"].lookup({"task_id": task_id, "model": model.name})

        for prompt_group in eval_.prompts:
            prompt_group_tuple = tuple([p.to_json() for p in prompt_group])
            prompt_id = db["evals_prompts"].lookup(
                {
                    "task_id": task_id,
                    "prompt_json": json.dumps(prompt_group_tuple),
                }
            )

            for case in eval_.cases:
                inputs = case.inputs
                inputs_json = json.dumps(inputs)
                case_id = db["evals_cases"].lookup(
                    {
                        "task_id": task_id,
                        "name": case.name,
                        "inputs_json": inputs_json,
                    },
                )

                for check in case.checks:
                    check_id = db["evals_checks"].lookup(
                        {
                            "task_id": task_id,
                            "case_id": case_id,
                            "name": check.name,
                            "value": check.value,
                        }
                    )

                    result_exists = list(
                        db["evals_checks_results"].rows_where(
                            "task_id = ? AND model_id = ? AND prompt_id = ? AND case_id = ? AND check_id = ?",
                            [task_id, model_id, prompt_id, case_id, check_id],
                        )
                    )

                    if not result_exists:
                        missing_results.append(
                            {
                                "task_id": task_id,
                                "model_id": model_id,
                                "model_name": model.name,
                                "prompt_id": prompt_id,
                                "prompt_group": prompt_group_tuple,
                                "case_id": case_id,
                                "case_name": case.name,
                                "case_inputs": case.inputs,
                                "check_id": check_id,
                                "check_name": check.name,
                                "check_value": check.value,
                            }
                        )

    return missing_results


def find_cached_response(db, prompt, system=None, model=None):
    """Search the llm db for this exact query, and return it if it already exists"""

    # TODO support options_json
    RESPONSE_SQL = """
    select * from responses
    where responses.model = :model
    and responses.prompt = :prompt
    and responses.system is :system
    order by datetime_utc desc
    limit 1;
    """
    rows = list(
        db.query(RESPONSE_SQL, {"prompt": prompt, "system": system, "model": model})
    )
    if len(rows):
        response = llm.Response.from_row(db, rows[0])
        return response


def run_eval(db, combination, checks):
    model = llm.get_model(combination["model_name"])
    prompt_group = combination["prompt_group"]

    # TODO consider all prompt groups when llm supports passing in multiple
    # prompts in the few-shot format
    # https://github.com/simonw/llm/issues/506
    user_prompt = next(p for p in prompt_group if p["type"] == "user").get("text")
    user_prompt_filled = user_prompt.format(**combination["case_inputs"])

    try:
        system_prompt = next(p for p in prompt_group if p["type"] == "system").get(
            "text"
        )
    except StopIteration:
        system_prompt = None

    response = find_cached_response(
        db, user_prompt_filled, system=system_prompt, model=combination["model_name"]
    )
    if response:
        response_id = response.id
    else:
        response = model.prompt(user_prompt_filled, system=system_prompt)
        response.log_to_db(db)

        # Query the database to find the latest response
        # TODO modify llm to make finding a response id easier?
        latest_response = list(
            db["responses"].rows_where(
                order_by="datetime_utc desc",
                limit=1,
            )
        )[0]
        response_id = latest_response["id"]

    check = {}
    check[combination["check_name"]] = combination["check_value"]
    actual_check = load_check(check, checks)
    result = actual_check(response)
    return (response_id, result)


def load_check(check, checks):
    if not isinstance(check, dict):
        raise ValueError("Check must be a dictionary")
    if len(check.keys()) != 1:
        raise ValueError("Check must have exactly one key")
    check_name, check_value = next(iter(check.items()))
    for check_class in checks:
        if check_class.name == check_name:
            return check_class(check_value)
    raise ValueError("Unknown check: {}".format(check))


def get_eval_results(db, eval_: Eval):
    task_id = db["evals_tasks"].lookup({"name": eval_.name})

    # Store the ids defined by this eval so we can query against them later
    model_ids = set()
    prompt_ids = set()
    case_ids = set()
    check_ids = set()

    for model in eval_.models:
        model_id = db["evals_models"].lookup({"task_id": task_id, "model": model.name})
        model_ids.add(model_id)
        for prompt_group in eval_.prompts:
            prompt_group_tuple = tuple([p.to_json() for p in prompt_group])
            prompt_id = db["evals_prompts"].lookup(
                {
                    "task_id": task_id,
                    "prompt_json": json.dumps(prompt_group_tuple),
                }
            )
            prompt_ids.add(prompt_id)

    for case in eval_.cases:
        inputs = case.inputs
        inputs_json = json.dumps(inputs)
        case_id = db["evals_cases"].lookup(
            {
                "task_id": task_id,
                "name": case.name,
                "inputs_json": inputs_json,
            },
        )
        case_ids.add(case_id)

        for check in case.checks:
            check_id = db["evals_checks"].lookup(
                {
                    "task_id": task_id,
                    "case_id": case_id,
                    "name": check.name,
                    "value": check.value,
                }
            )
            check_ids.add(check_id)

    # Create temporary tables for ids in this eval
    db["temp_model_ids"].insert_all([{"id": id} for id in model_ids])
    db["temp_prompt_ids"].insert_all([{"id": id} for id in prompt_ids])
    db["temp_case_ids"].insert_all([{"id": id} for id in case_ids])
    db["temp_check_ids"].insert_all([{"id": id} for id in check_ids])

    query = """
    SELECT 
        ecr.id AS result_id,
        em.model,
        ep.prompt_json,
        ec.inputs_json,
        ec.id,
        eck.name AS check_name,
        eck.value AS check_value,
        res.response AS response,
        ecr.result
    FROM evals_checks_results ecr
    JOIN evals_models em ON ecr.model_id = em.id
    JOIN evals_prompts ep ON ecr.prompt_id = ep.id
    JOIN evals_cases ec ON ecr.case_id = ec.id
    JOIN evals_checks eck ON ecr.check_id = eck.id
    JOIN responses res ON ecr.response_id = res.id

    -- Join by this eval's ids so we don't include outdated combinations
    JOIN temp_model_ids tmi ON ecr.model_id = tmi.id
    JOIN temp_prompt_ids tpi ON ecr.prompt_id = tpi.id
    JOIN temp_case_ids tci ON ecr.case_id = tci.id
    JOIN temp_check_ids thi ON ecr.check_id = thi.id

    WHERE ecr.task_id = ?
    """
    results = list(db.query(query, [task_id]))

    # Clean up temporary tables
    db["temp_model_ids"].drop()
    db["temp_prompt_ids"].drop()
    db["temp_case_ids"].drop()
    db["temp_check_ids"].drop()

    return results


def calculate_aggregates(eval_, results):
    grouped_data = {}

    # Group data by model, prompt_json
    for row in results:
        key = (row["model"], row["prompt_json"])

        if key not in grouped_data:
            grouped_data[key] = {
                "model": row["model"],
                "prompt_json": row["prompt_json"],
                "total_checks": 0,
                "correct_checks": 0,
            }

        grouped_data[key]["total_checks"] += 1
        grouped_data[key]["correct_checks"] += row["result"]

    # Convert to list and calculate accuracy
    aggregated_results = []
    for group in grouped_data.values():
        accuracy = (
            group["correct_checks"] / group["total_checks"]
            if group["total_checks"] > 0
            else 0
        )
        group["accuracy"] = accuracy
        aggregated_results.append(group)

    return aggregated_results

@llm.hookimpl
def register_eval_checks():
    return checks.classes

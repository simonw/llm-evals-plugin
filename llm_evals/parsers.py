import json
import csv
from os import path
from typing import Dict, Tuple
from llm_evals.models import Case, Check, Eval, Model, Prompt


def parse_prompts(prompts_data) -> Tuple[Tuple[Prompt]]:
    prompts = []
    if isinstance(prompts_data, str):
        prompts.append((Prompt(text=prompts_data, type="user"),))
    elif isinstance(prompts_data, list):
        # If all elements are dicts, treat as a single conversation
        if all(isinstance(p, dict) for p in prompts_data):
            conversation = []
            for item in prompts_data:
                if isinstance(item, str):
                    conversation.append(Prompt(text=item, type="user"))
                else:
                    conversation.append(Prompt(**item))
            prompts.append(tuple(conversation))

        # Otherwise process as multiple conversations
        else:
            for item in prompts_data:
                if isinstance(item, str):
                    prompts.append((Prompt(text=item, type="user"),))
                elif isinstance(item, dict):
                    prompts.append((Prompt(**item),))
                elif isinstance(item, list):
                    prompts.append(
                        tuple(
                            (
                                Prompt(text=p, type="user")
                                if isinstance(p, str)
                                else Prompt(**p)
                            )
                            for p in item
                        )
                    )

    return tuple(prompts)


def parse_models(models_data) -> Tuple[Model]:
    models = []
    if isinstance(models_data, str):
        models.append(Model(name=models_data, options={}))
    elif isinstance(models_data, list):
        for model_data in models_data:
            if isinstance(model_data, str):
                models.append(Model(name=model_data, options={}))
            else:
                name = model_data.get("name")
                options = model_data.get("options", {})
                models.append(Model(name=name, options=options))
    return tuple(models)


def parse_cases(cases_data, base_dir=None) -> Tuple[Case]:
    cases = []
    if isinstance(cases_data, str) and cases_data.endswith(".csv"):
        if not base_dir:
            raise ValueError("base_dir is required when loading .csv")

        cases_filename = path.join(base_dir, cases_data)
        cases_data = []
        with open(cases_filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # TODO reraise more helpful errors on json decode issues
                inputs = row.get("inputs")
                checks = row.get("checks")
                cases_data.append(
                    {
                        "name": row.get("name"),
                        "checks": json.loads(checks or "[]"),
                        "inputs": json.loads(inputs or "{}"),
                    }
                )

    for case_data in cases_data:
        name = case_data.get("name")
        checks_data = case_data.get("checks", [])
        inputs = case_data.get("inputs", {})

        checks = []
        for check_data in checks_data:
            check_name = list(check_data.keys())[0]
            check_value = check_data[check_name]
            checks.append(Check(name=check_name, value=check_value))

        cases.append(Case(name=name, checks=tuple(checks), inputs=inputs))

    return tuple(cases)


def parse_eval(data: Dict, base_dir: str) -> Eval:
    """
    Build up an Eval object from a Python dict (likely originally from a
    yaml or json file).

    See tests/test_parsers.py for more details
    """
    prompts = parse_prompts(data.get("prompts"))
    models = parse_models(data.get("models"))
    cases = parse_cases(data.get("cases"), base_dir)

    return Eval(
        ev=data.get("ev", ""),
        name=data.get("name", ""),
        prompts=prompts,
        models=models,
        cases=cases,
    )

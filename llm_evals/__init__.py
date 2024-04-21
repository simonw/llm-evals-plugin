import click
import llm
import yaml


from llm.plugins import pm
from . import hookspecs
from . import checks

pm.add_hookspecs(hookspecs)


@llm.hookimpl
def register_commands(cli):
    @cli.command()
    @click.argument("evals", nargs=-1, required=True, type=click.Path(exists=True))
    @click.option("models", "-m", "--model", multiple=True)
    def evals(evals, models):
        "Run evals against models"
        checks = []
        for check in pm.hook.register_eval_checks():
            checks.extend(check)

        for eval_path in evals:
            with open(eval_path) as f:
                eval_ = yaml.safe_load(f)
                for model_id in models:
                    model = llm.get_model(model_id)
                    result = run_eval(eval_, model, checks)
                    click.echo((model.model_id, result))


def run_eval(eval_, model, checks):
    prompt = eval_["prompt"]
    system = eval_.get("system", None)
    response = model.prompt(prompt, system=system)
    passes = []
    for check in eval_["checks"]:
        actual_check = load_check(check, checks)
        passes.append(actual_check(response))
    return passes


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


@llm.hookimpl
def register_eval_checks():
    return checks.classes

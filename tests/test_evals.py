from llm.plugins import load_plugins, pm
import pytest
import sqlite_utils
import json
from ulid import ULID
import datetime
from unittest.mock import patch

from llm_evals import (
    find_cached_response,
    get_missing_results,
    get_model_prompt_performance,
)
from llm_evals.migrations import migrate
from llm_evals.models import Case, Check, Eval, Model, Prompt


def test_plugin_is_installed():
    load_plugins()
    names = [mod.__name__ for mod in pm.get_plugins()]
    assert "llm_evals" in names


@pytest.fixture
def evals_fixture(user_path):
    log_path = str(user_path / "logs.db")
    db = sqlite_utils.Database(log_path)
    migrate(db)

    db["evals_tasks"].insert({"id": 1, "name": "Test eval"})
    db["evals_models"].insert(
        {
            "id": 1,
            "task_id": 1,
            "model": "gpt-4o-mini",
        }
    )
    db["evals_prompts"].insert(
        {
            "id": 1,
            "task_id": 1,
            "prompt_json": json.dumps(
                [{"type": "user", "text": "What comes {before_after} {number}"}]
            ),
        }
    )
    db["evals_cases"].insert(
        {
            "id": 1,
            "task_id": 1,
            "name": "increment",
            "inputs_json": json.dumps({"before_after": "after", "number": 5885}),
        }
    )
    db["evals_cases"].insert(
        {
            "id": 2,
            "task_id": 1,
            "name": "decrement",
            "inputs_json": json.dumps({"before_after": "before", "number": 4284}),
        }
    )
    db["evals_checks"].insert({"id": 1, "task_id": 1, "name": "exact"})
    db["evals_checks_results"].insert(
        {
            "id": 1,
            "task_id": 1,
            "model_id": 1,
            "prompt_id": 1,
            "case_id": 1,
            "check_id": 1,
            "result": 1,
        }
    )
    db["evals_checks_results"].insert(
        {
            "id": 2,
            "task_id": 1,
            "model_id": 1,
            "prompt_id": 1,
            "case_id": 2,
            "check_id": 1,
            "result": 1,
        }
    )

    return log_path


def test_get_missing_results_base(evals_fixture):
    db = sqlite_utils.Database(evals_fixture)
    eval_ = Eval(
        ev="0.1",
        name="Test eval",
        models=(Model(name="gpt-4o-mini", options={}),),
        prompts=((Prompt(type="user", text="What comes {before_after} {number}"),),),
        cases=(
            Case(
                name="increment",
                inputs={"before_after": "after", "number": 5885},
                checks=(Check(name="exact", value="5886"),),
            ),
            Case(
                name="decrement",
                inputs={"before_after": "before", "number": 4284},
                checks=(Check(name="exact", value="4283"),),
            ),
        ),
    )
    actual = get_missing_results(db, eval_)
    assert len(actual) == 2


def test_get_missing_results_additional_model(evals_fixture):
    db = sqlite_utils.Database(evals_fixture)
    eval_ = Eval(
        ev="0.1",
        name="Test eval",
        models=(
            Model(name="gpt-4o-mini", options={}),
            Model(name="claude-3-haiku", options={}),
        ),
        prompts=((Prompt(type="user", text="What comes {before_after} {number}"),),),
        cases=(
            Case(
                name="increment",
                inputs={"before_after": "after", "number": 5885},
                checks=(Check(name="exact", value="5886"),),
            ),
            Case(
                name="decrement",
                inputs={"before_after": "before", "number": 4284},
                checks=(Check(name="exact", value="4283"),),
            ),
        ),
    )
    actual = get_missing_results(db, eval_)
    assert len(actual) == 4


def test_get_missing_results_new_model(evals_fixture):
    db = sqlite_utils.Database(evals_fixture)
    eval_ = Eval(
        ev="0.1",
        name="Test eval",
        models=(Model(name="claude-3-haiku", options={}),),
        prompts=((Prompt(type="user", text="What comes {before_after} {number}"),),),
        cases=(
            Case(
                name="increment",
                inputs={"before_after": "after", "number": 5885},
                checks=(Check(name="exact", value="5886"),),
            ),
            Case(
                name="decrement",
                inputs={"before_after": "before", "number": 4284},
                checks=(Check(name="exact", value="4283"),),
            ),
        ),
    )
    actual = get_missing_results(db, eval_)
    assert len(actual) == 2
    assert actual[0]["model_name"] == "claude-3-haiku"


def test_get_missing_results_new_model_fewer_cases(evals_fixture):
    db = sqlite_utils.Database(evals_fixture)
    eval_ = Eval(
        ev="0.1",
        name="Test eval",
        models=(Model(name="claude-3-haiku", options={}),),
        prompts=((Prompt(type="user", text="What comes {before_after} {number}"),),),
        cases=(
            Case(
                name="increment",
                inputs={"before_after": "after", "number": 5885},
                checks=(Check(name="exact", value="5886"),),
            ),
        ),
    )
    actual = get_missing_results(db, eval_)
    assert len(actual) == 1
    assert actual[0]["model_name"] == "claude-3-haiku"


@pytest.fixture
def logs_fixture(user_path):
    log_path = str(user_path / "logs.db")
    db = sqlite_utils.Database(log_path)
    migrate(db)

    start = datetime.datetime.now(datetime.timezone.utc)
    db["responses"].insert_all(
        {
            "id": str(ULID()).lower(),
            "system": "system",
            "prompt": "prompt",
            "response": 'response\n```python\nprint("hello word")\n```',
            "model": "davinci",
            "datetime_utc": (start + datetime.timedelta(seconds=i)).isoformat(),
            "conversation_id": "abc123",
            "input_tokens": 2,
            "output_tokens": 5,
        }
        for i in range(100)
    )

    return log_path


def test_find_cached_response(logs_fixture):
    db = sqlite_utils.Database(logs_fixture)
    with patch("llm.Response.from_row", autospec=True) as mock_from_row:
        find_cached_response(db, "prompt", model="davinci", system="system")
        _db, row = mock_from_row.call_args.args

        assert row["model"] == "davinci"


def test_find_cached_response_missing(logs_fixture):
    db = sqlite_utils.Database(logs_fixture)
    with patch("llm.Response.from_row", autospec=True) as mock_from_row:
        find_cached_response(db, "prompt", model="claude-3-haiku", system="system")
        mock_from_row.assert_not_called()


def test_get_model_prompt_performance_base(evals_fixture):
    db = sqlite_utils.Database(evals_fixture)
    eval_ = Eval(
        ev="0.1",
        name="Test eval",
        models=(Model(name="gpt-4o-mini", options={}),),
        prompts=((Prompt(type="user", text="What comes {before_after} {number}"),),),
        cases=(
            Case(
                name="increment",
                inputs={"before_after": "after", "number": 5885},
                checks=(Check(name="exact", value="5886"),),
            ),
            Case(
                name="decrement",
                inputs={"before_after": "before", "number": 4284},
                checks=(Check(name="exact", value="4283"),),
            ),
        ),
    )
    actual = get_model_prompt_performance(db, eval_)
    assert len(actual.keys()) == 1
    assert next(iter(actual.values()))["total_cases"] == 2


def test_get_model_prompt_performance_extra(evals_fixture):
    db = sqlite_utils.Database(evals_fixture)

    eval_ = Eval(
        ev="0.1",
        name="Test eval",
        models=(Model(name="gpt-4o-mini", options={}),),
        prompts=((Prompt(type="user", text="What comes {before_after} {number}"),),),
        cases=(
            Case(
                name="increment",
                inputs={"before_after": "after", "number": 5885},
                checks=(Check(name="exact", value="5886"),),
            ),
            Case(
                name="decrement",
                inputs={"before_after": "before", "number": 4284},
                checks=(Check(name="exact", value="4283"),),
            ),
        ),
    )

    # This case is NOT specified above, so it should not be included in the output
    db["evals_cases"].insert(
        {
            "id": 3,
            "task_id": 1,
            "name": "decrement 2",
            "inputs_json": json.dumps({"before_after": "before", "number": 4284}),
        }
    )
    db["evals_checks_results"].insert(
        {
            "id": 3,
            "task_id": 1,
            "model_id": 1,
            "prompt_id": 1,
            "case_id": 3,
            "check_id": 1,
            "result": 0,
        }
    )

    actual = get_model_prompt_performance(db, eval_)
    assert len(actual.keys()) == 1
    case_1 = next(iter(actual.values()))
    assert case_1["total_cases"] == 2
    assert case_1["accuracy"] == 100

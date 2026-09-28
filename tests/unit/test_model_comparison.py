import asyncio
import json
from types import SimpleNamespace

import pytest

from agent_lab import model_comparison as app
from agent_lab.config import Settings
from agent_lab.logging_config import current_run_id

ARGUMENTS = {"source": ["A", "B", "B"], "baseline": ["B", "C"]}
MODELS = {"openai": "gpt-test", "anthropic": "claude-test"}
EXPECTED = {"same": ["B"], "source_only": ["A"], "baseline_only": ["C"]}


def result():
    return SimpleNamespace(
        final_output="done",
        new_items=[
            SimpleNamespace(
                type="tool_call_item",
                raw_item=SimpleNamespace(
                    name="compare_lists", arguments=json.dumps(ARGUMENTS), call_id="one"
                ),
            ),
            SimpleNamespace(
                type="tool_call_output_item",
                raw_item={"call_id": "one"},
                output=json.dumps(EXPECTED),
            ),
        ],
    )


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-anthropic")


def test_parallel_tasks_have_independent_state(monkeypatch, keys):
    observed = {}
    ready = asyncio.Event()

    async def fake_agent(prompt, model, settings):
        observed[settings.provider] = (
            current_run_id(),
            model,
            settings.tracing_enabled,
            prompt,
        )
        if len(observed) == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), 1)
        return result()

    monkeypatch.setattr(app, "run_agent", fake_agent)
    report = asyncio.run(app.compare_models(ARGUMENTS, MODELS, Settings()))
    assert report["status"] == "success"
    assert report["results_match"] is True
    assert [run["provider"] for run in report["runs"]] == ["openai", "anthropic"]
    ids = {report["batch_run_id"], *(run["run_id"] for run in report["runs"])}
    assert len(ids) == 3
    assert observed["openai"][1:3] == ("gpt-test", False)
    assert observed["anthropic"][1:3] == ("claude-test", False)
    assert observed["openai"][3] == observed["anthropic"][3]
    assert current_run_id() == "-"


@pytest.mark.parametrize(
    "error", [RuntimeError("private-marker"), TimeoutError("private-marker")]
)
def test_one_failure_preserves_other_result(monkeypatch, keys, error, caplog):
    async def fake_agent(prompt, model, settings):
        if settings.provider == "openai":
            raise error
        await asyncio.sleep(0)
        return result()

    monkeypatch.setattr(app, "run_agent", fake_agent)
    report = asyncio.run(app.compare_models(ARGUMENTS, MODELS, Settings()))
    assert report["status"] == "failed"
    assert report["results_match"] is None
    assert report["runs"][0]["error"]["type"] == type(error).__name__
    assert report["runs"][1]["status"] == "success"
    assert report["runs"][1]["comparison"] == EXPECTED
    assert "private-marker" not in json.dumps(report) + caplog.text


@pytest.mark.parametrize(
    "problem",
    [
        "missing",
        "multiple",
        "wrong_arguments",
        "wrong_id",
        "error_json",
        "wrong_result",
    ],
)
def test_tool_contract_is_checked(monkeypatch, keys, problem):
    async def fake_agent(*args):
        value = result()
        if problem == "missing":
            value.new_items = []
        elif problem == "multiple":
            value.new_items *= 2
        elif problem == "wrong_arguments":
            value.new_items[0].raw_item.arguments = '{"source":[],"baseline":[]}'
        elif problem == "wrong_id":
            value.new_items[1].raw_item["call_id"] = "different"
        elif problem == "error_json":
            value.new_items[1].output = '{"error":{"code":"INVALID_INPUT"}}'
        else:
            value.new_items[
                1
            ].output = '{"same":[],"source_only":[],"baseline_only":[]}'
        return value

    monkeypatch.setattr(app, "run_agent", fake_agent)
    report = asyncio.run(app.compare_models(ARGUMENTS, MODELS, Settings()))
    assert report["status"] == "failed"
    assert all(run["error"]["kind"] == "tool_contract_error" for run in report["runs"])


def test_cancellation_waits_for_both_tasks(monkeypatch, keys):
    entered = set()
    closed = set()
    ready = asyncio.Event()

    async def fake_agent(prompt, model, settings):
        entered.add(settings.provider)
        if len(entered) == 2:
            ready.set()
        try:
            await asyncio.Event().wait()
        finally:
            closed.add(settings.provider)

    async def execute():
        task = asyncio.create_task(app.compare_models(ARGUMENTS, MODELS, Settings()))
        await asyncio.wait_for(ready.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed == {"openai", "anthropic"}

    monkeypatch.setattr(app, "run_agent", fake_agent)
    asyncio.run(execute())


def test_missing_key_stops_cli_before_api(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    async def forbidden(*args):
        raise AssertionError("Must not make any paid request")

    monkeypatch.setattr(app, "compare_models", forbidden)
    with pytest.raises(SystemExit) as error:
        app.cli(
            [
                "--openai-model",
                "gpt-test",
                "--anthropic-model",
                "claude-test",
                "--arguments",
                json.dumps(ARGUMENTS),
            ]
        )
    assert error.value.code == 2
    assert "ANTHROPIC_API_KEY is required" in capsys.readouterr().err


@pytest.mark.parametrize("success", [True, False])
def test_cli_json_and_exit_status(monkeypatch, keys, capsys, success):
    monkeypatch.setenv("AGENT_PROVIDER", "anthropic")
    monkeypatch.setenv("AGENT_TRACING_ENABLED", "true")

    async def fake_comparison(arguments, models, settings):
        assert models == MODELS
        assert settings.tracing_enabled is False
        return {"status": "success" if success else "failed"}

    monkeypatch.setattr(app, "compare_models", fake_comparison)
    code = app.cli(
        [
            "--openai-model",
            "gpt-test",
            "--anthropic-model",
            "claude-test",
            "--arguments",
            json.dumps(ARGUMENTS),
        ]
    )
    assert code == (0 if success else 1)
    assert json.loads(capsys.readouterr().out)["status"] == (
        "success" if success else "failed"
    )

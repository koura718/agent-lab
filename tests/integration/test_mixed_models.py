"""Two independent real Runner/Tool executions with deterministic local models."""

import asyncio
from contextlib import asynccontextmanager

import pytest
from agents.testing import ScriptedModel, assistant_message, function_call

from agent_lab import main as agent_main
from agent_lab.config import Settings
from agent_lab.model_comparison import compare_models

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("mode", ["function", "mcp"])
def test_parallel_runner_paths(monkeypatch, mode, child_processes):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-anthropic")
    arguments = {"source": ["A", "B", "B"], "baseline": ["B", "C"]}
    seen = {}

    @asynccontextmanager
    async def scripted(settings, model):
        instance = ScriptedModel(
            [
                [function_call("compare_lists", arguments, call_id=settings.provider)],
                [assistant_message(settings.provider + " finished")],
            ]
        )
        seen[settings.provider] = instance
        yield instance
        instance.assert_complete()

    monkeypatch.setattr(agent_main, "configured_model", scripted)
    report = asyncio.run(
        compare_models(
            arguments,
            {"openai": "gpt-test", "anthropic": "claude-test"},
            Settings(tool_mode=mode),
        )
    )
    assert report["status"] == "success"
    assert report["results_match"] is True
    assert set(seen) == {"openai", "anthropic"}
    assert report["runs"][0]["final_output"] == "openai finished"
    assert report["runs"][1]["final_output"] == "anthropic finished"
    assert len(child_processes) == (2 if mode == "mcp" else 0)
    assert all(process.returncode == 0 for process, _ in child_processes)

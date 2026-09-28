"""Real Runner and HTTP adapter, mocked model API, real MCP subprocess."""

import asyncio
import json

import httpx2 as httpx
import pytest
from openai import AsyncOpenAI

from agent_lab import model_provider
from agent_lab.config import Settings
from agent_lab.main import run_agent

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("mode", ["function", "mcp"])
def test_claude_tool_roundtrip(monkeypatch, mode):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-send-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://must-not-use.invalid/")
    requests = []
    clients = []

    def handle(request):
        assert str(request.url) == "https://api.anthropic.com/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer anthropic-test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "claude-test-model"
        assert any(
            tool["function"]["name"] == "compare_lists" for tool in payload["tools"]
        )
        requests.append(payload)
        if len(requests) == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "toolu_test123",
                        "type": "function",
                        "function": {
                            "name": "compare_lists",
                            "arguments": '{"source":["A","B","B"],"baseline":["B","C"]}',
                        },
                    }
                ],
            }
            reason = "tool_calls"
        else:
            tool_message = next(m for m in payload["messages"] if m["role"] == "tool")
            assert tool_message["tool_call_id"] == "toolu_test123"
            assert json.loads(tool_message["content"]) == {
                "same": ["B"],
                "source_only": ["A"],
                "baseline_only": ["C"],
            }
            message = {"role": "assistant", "content": "Comparison complete."}
            reason = "stop"
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl_test",
                "object": "chat.completion",
                "created": 1,
                "model": "claude-test-model",
                "choices": [{"index": 0, "message": message, "finish_reason": reason}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )

    def create_client(**kwargs):
        client = AsyncOpenAI(
            **kwargs,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
        )
        clients.append(client)
        return client

    monkeypatch.setattr(model_provider, "AsyncOpenAI", create_client)
    result = asyncio.run(
        run_agent(
            "Compare the lists.",
            "claude-test-model",
            Settings(provider="anthropic", tool_mode=mode),
        )
    )
    assert result.final_output == "Comparison complete."
    assert len(requests) == 2
    assert clients[0].is_closed()


@pytest.mark.parametrize(
    "error", [RuntimeError("private-marker"), asyncio.CancelledError()]
)
def test_anthropic_client_closed_on_error(monkeypatch, error):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    clients = []

    def create_client(**kwargs):
        client = AsyncOpenAI(
            **kwargs,
            http_client=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda request: httpx.Response(500))
            ),
        )
        clients.append(client)
        return client

    monkeypatch.setattr(model_provider, "AsyncOpenAI", create_client)

    async def execute():
        async with model_provider.configured_model(
            Settings(provider="anthropic"), "claude-test-model"
        ):
            raise error

    with pytest.raises(type(error)):
        asyncio.run(execute())
    assert clients[0].is_closed()

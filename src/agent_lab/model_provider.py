"""Explicit provider selection for model evaluation; no global SDK changes."""

import os
from contextlib import asynccontextmanager

from agents import Model, OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from agent_lab.config import ConfigurationError, Settings

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1/"


def validate_model_access(settings: Settings, model: str | Model | None) -> None:
    """Validate credentials without including their values in errors."""
    if settings.provider == "anthropic":
        if settings.tracing_enabled:
            raise ConfigurationError("Claude evaluation requires --no-tracing.")
        if not isinstance(model, str) or not model.strip():
            raise ConfigurationError(
                "Anthropic requires an explicit --model or AGENT_MODEL."
            )
        key_name = "ANTHROPIC_API_KEY"
    else:
        key_name = "OPENAI_API_KEY"
    if not os.getenv(key_name, "").strip():
        raise ConfigurationError(f"{key_name} is required for a model-backed run.")


@asynccontextmanager
async def configured_model(settings: Settings, model: str | Model | None):
    """Own and close the Anthropic compatibility client, even on cancellation."""
    if settings.provider == "openai":
        # Preserve ScriptedModel and the SDK's existing OpenAI resolution.
        yield model
        return
    validate_model_access(settings, model)
    async with AsyncOpenAI(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        base_url=ANTHROPIC_BASE_URL,
        # Do not inherit OpenAI account selection for another provider.
        organization="",
        project="",
        max_retries=0,
        timeout=settings.run_timeout_seconds,
    ) as client:
        yield OpenAIChatCompletionsModel(model=model, openai_client=client)

"""CLI for offline comparison and explicit model-backed Agent runs."""

import argparse
import asyncio
import json
import logging
import os

from agents import Model, RunConfig, Runner

from agent_lab.agent_factory import create_agent
from agent_lab.config import (
    ConfigurationError,
    Settings,
    add_settings_arguments,
    load_settings,
)
from agent_lab.mcp.connection import agent_connection
from agent_lab.tools.list_tools import compare_json

DEFAULT_PROMPT = (
    "OpenAI Agents SDK が正常に動作していることを日本語で短く確認してください。"
)
logger = logging.getLogger(__name__)


async def run_agent(prompt: str, model: str | Model | None, settings: Settings):
    async with asyncio.timeout(settings.run_timeout_seconds):
        if settings.tool_mode == "mcp":
            async with agent_connection(settings) as server:
                return await Runner.run(
                    create_agent(model=model, mcp_server=server),
                    prompt,
                    max_turns=settings.max_turns,
                    run_config=RunConfig(tracing_disabled=True),
                )
        return await Runner.run(
            create_agent(model=model),
            prompt,
            max_turns=settings.max_turns,
            run_config=RunConfig(tracing_disabled=True),
        )


async def main(
    prompt: str = DEFAULT_PROMPT,
    model: str | None = None,
    settings: Settings | None = None,
) -> None:
    result = await run_agent(prompt, model, settings or Settings())
    print(result.final_output)


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--compare-json", help="Compare a JSON object locally; no API.")
    inputs.add_argument(
        "--prompt", help="Send this prompt to the model (API charges apply)."
    )
    add_settings_arguments(parser)
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args)
    except ConfigurationError as error:
        parser.error(str(error))
    if args.compare_json is not None and settings.tool_mode != "function":
        parser.error(
            "--compare-json is local-only; use the MCP diagnostic CLI for MCP calls."
        )
    logging.basicConfig(
        level=settings.log_level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    if args.compare_json is not None:
        output = compare_json(args.compare_json)
        print(output)
        return 2 if "error" in json.loads(output) else 0
    if not os.getenv("OPENAI_API_KEY", "").strip():
        logger.error("OPENAI_API_KEY is required for a model-backed run.")
        return 2
    try:
        logger.info("Starting Agent")
        asyncio.run(
            main(
                args.prompt if args.prompt is not None else DEFAULT_PROMPT,
                settings.model,
                settings,
            )
        )
    except KeyboardInterrupt:
        logger.warning("Agent interrupted")
        return 130
    except Exception as error:  # noqa: BLE001 - sanitize errors at the CLI boundary
        # Exception messages may include request data or credentials.
        logger.error(
            "Agent failed (%s). Check configuration and connectivity.",
            type(error).__name__,
        )
        return 1
    logger.info("Agent completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())

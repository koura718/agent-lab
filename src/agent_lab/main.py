"""CLI for offline comparison and explicit model-backed Agent runs."""

import argparse
import asyncio
import json
import logging
import os

from agents import RunConfig, Runner

from agent_lab.agent_factory import create_agent
from agent_lab.tools.list_tools import compare_json

DEFAULT_PROMPT = (
    "OpenAI Agents SDK が正常に動作していることを日本語で短く確認してください。"
)
logger = logging.getLogger(__name__)


async def main(prompt: str = DEFAULT_PROMPT, model: str | None = None) -> None:
    async with asyncio.timeout(60):
        result = await Runner.run(
            create_agent(model=model),
            prompt,
            max_turns=5,
            run_config=RunConfig(tracing_disabled=True),
        )
    print(result.final_output)


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--compare-json", help="Compare a JSON object locally; no API.")
    inputs.add_argument(
        "--prompt", help="Send this prompt to the model (API charges apply)."
    )
    parser.add_argument("--model", default=os.getenv("AGENT_MODEL") or None)
    parser.add_argument("--tool-mode", choices=["function"], default="function")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
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
            main(args.prompt if args.prompt is not None else DEFAULT_PROMPT, args.model)
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

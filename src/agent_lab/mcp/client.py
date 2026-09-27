"""Diagnostic MCP CLI. Starts the bundled local server; never calls a model."""

import argparse
import asyncio
import json
import logging

from agent_lab.config import (
    ConfigurationError,
    Settings,
    add_settings_arguments,
    load_settings,
)
from agent_lab.mcp.connection import diagnostic_connection

logger = logging.getLogger(__name__)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys.")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Invalid JSON constant.")


def parse_arguments(raw: str) -> dict:
    try:
        result = json.loads(
            raw, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
    except (ValueError, RecursionError) as error:
        raise ConfigurationError(
            "arguments must be valid JSON without duplicate keys."
        ) from error
    if not isinstance(result, dict):
        raise ConfigurationError("arguments must be a JSON object.")
    return result


async def execute(
    command: str,
    settings: Settings,
    tool: str | None = None,
    arguments: dict | None = None,
) -> tuple[dict, int]:
    async with asyncio.timeout(settings.run_timeout_seconds):
        async with diagnostic_connection(settings) as client:
            if command == "list-tools":
                result = await client.list_tools()
                return {
                    "tools": [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in result.tools
                    ]
                }, 0
            result = await client.call_tool(tool, arguments)
            if result.is_error:
                logger.error("MCP tool returned an error")
                return {
                    "error": {
                        "code": "MCP_TOOL_ERROR",
                        "message": "Tool rejected the request.",
                    }
                }, 1
            value = result.structured_content
            if not isinstance(value, dict) or set(value) != {
                "same",
                "source_only",
                "baseline_only",
            }:
                raise ValueError("Invalid comparison response.")
            if any(
                not isinstance(items, list)
                or any(not isinstance(item, str) for item in items)
                for items in value.values()
            ):
                raise ValueError("Invalid comparison response.")
            return value, 0


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_settings_arguments(parser)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-tools")
    call = commands.add_parser("call")
    call.add_argument("tool")
    call.add_argument("--arguments", required=True)
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args)
        arguments = parse_arguments(args.arguments) if args.command == "call" else None
    except ConfigurationError as error:
        parser.error(str(error))
    logging.basicConfig(
        level=settings.log_level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    try:
        output, code = asyncio.run(
            execute(args.command, settings, getattr(args, "tool", None), arguments)
        )
    except KeyboardInterrupt:
        logger.warning("MCP client interrupted")
        return 130
    except Exception as error:  # noqa: BLE001 - sanitized CLI boundary
        logger.error("MCP client failed (%s)", type(error).__name__)
        return 1
    print(json.dumps(output, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(cli())

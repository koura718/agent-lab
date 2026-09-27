"""Build Agents without performing model requests."""

from agents import Agent, Model
from agents.mcp import MCPServer

from agent_lab.tools.list_tools import create_compare_lists_tool


def create_agent(
    *, model: str | Model | None = None, mcp_server: MCPServer | None = None
) -> Agent:
    return Agent(
        name="Assistant",
        instructions=(
            "You are a concise and reliable AI development assistant. "
            "Answer in Japanese unless instructed otherwise. "
            "Use compare_lists when asked to compare two string lists. "
            "Preserve the user's values exactly. If a list is missing, ask for it. "
            "Report tool input errors; never invent a successful comparison."
        ),
        model=model,
        tools=[] if mcp_server is not None else [create_compare_lists_tool()],
        mcp_servers=[mcp_server] if mcp_server is not None else [],
    )

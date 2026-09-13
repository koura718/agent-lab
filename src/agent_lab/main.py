import asyncio

from agents import Agent, Runner

agent = Agent(
    name="Assistant",
    instructions=(
        "You are a concise and reliable AI development assistant. "
        "Answer in Japanese unless instructed otherwise."
    ),
)


async def main() -> None:
    result = await Runner.run(
        agent,
        "OpenAI Agents SDK が正常に動作していることを日本語で短く確認してください。",
    )
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())

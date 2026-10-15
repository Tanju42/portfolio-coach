import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.agent import Agent, ToolSpec
from app.llm import AssistantReply, ToolCall


class FakeChatClient:
    def __init__(self, replies: list[AssistantReply]) -> None:
        self._replies = list(replies)
        self.requests: list[tuple[list[dict], list[dict]]] = []

    async def complete(self, messages, tools):
        self.requests.append((messages, tools))
        return self._replies.pop(0)


async def get_price(args):
    return {"symbol": args["symbol"], "price_usd": 42000.0}


@pytest.mark.anyio
async def test_agent_calls_tool_then_answers():
    client = FakeChatClient(
        [
            AssistantReply(
                content="",
                tool_calls=(ToolCall(call_id="c1", name="get_price", arguments={"symbol": "BTC"}),),
            ),
            AssistantReply(content="BTC trades at $42000.", tool_calls=()),
        ]
    )
    agent = Agent(
        client,
        [
            ToolSpec(
                name="get_price",
                description="Get current price of a crypto symbol",
                parameters={
                    "type": "object",
                    "properties": {"symbol": {"type": "string"}},
                    "required": ["symbol"],
                },
                handler=get_price,
            )
        ],
    )
    history = [{"role": "user", "content": "What is the current BTC price?"}]

    result = await agent.run(history)

    assert result.content == "BTC trades at $42000."
    assert result.tool_trace[0]["name"] == "get_price"
    assert result.tool_trace[0]["result"] == {"symbol": "BTC", "price_usd": 42000.0}
    tool_messages = [m for m in client.requests[-1][0] if m["role"] == "tool"]
    assert tool_messages[0]["tool_call_id"] == "c1"


@pytest.mark.anyio
async def test_agent_survives_unknown_tool():
    client = FakeChatClient(
        [
            AssistantReply(content="", tool_calls=(ToolCall(call_id="c2", name="nope", arguments={}),)),
            AssistantReply(content="Sorry, that tool is unavailable.", tool_calls=()),
        ]
    )
    agent = Agent(client, [])

    result = await agent.run([{"role": "user", "content": "do something"}])

    assert "unavailable" in result.content
    assert "unknown tool" in result.tool_trace[0]["result"]["error"]

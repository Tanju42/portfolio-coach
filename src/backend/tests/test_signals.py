import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import ToolSpec
from app.coach import CoachAgent, BEGINNER_SYSTEM_PROMPT
from app.llm import AssistantReply, ToolCall
from app.memory import MemoryStore

needs_model = pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="local LLM endpoint not configured",
)


class FakeChatClient:
    def __init__(self, replies):
        self._replies = list(replies)
        self.requests = []

    async def complete(self, messages, tools):
        self.requests.append((messages, tools))
        return self._replies.pop(0)


class StubMCPManager:
    async def list_tool_specs(self):
        async def get_ticker(args):
            return {"last_price": "150.0", "price_change_percent_24h": "-3.2"}

        return [
            ToolSpec(
                name="binance_get_ticker",
                description="24h ticker",
                parameters={
                    "type": "object",
                    "properties": {"symbol": {"type": "string"}},
                    "required": ["symbol"],
                },
                handler=get_ticker,
            )
        ]


@pytest.mark.anyio
async def test_signal_tool_delivers_structured_signal():
    db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    store = MemoryStore(db)
    signal_args = {
        "action": "HOLD",
        "symbol": "SOL",
        "confidence": 55,
        "risk_level": "medium",
        "headline": "SOL is down 3% today; no urgent action needed.",
        "rationale": ["24h change negative", "Position is small relative to portfolio"],
        "beginner_explanation": "Doing nothing is a valid choice.",
        "disclaimer": "educational",
    }
    client = FakeChatClient(
        [
            AssistantReply(
                content="",
                tool_calls=(ToolCall(call_id="c1", name="deliver_signal", arguments=signal_args),),
            ),
            AssistantReply(content="I recommend HOLD for now.", tool_calls=()),
        ]
    )
    coach = CoachAgent(client, store)
    agent = await coach.build(StubMCPManager())

    result = await coach.run(agent, [{"role": "user", "content": "Should I sell my SOL?"}])

    assert result["signal"]["action"] == "HOLD"
    assert result["signal"]["confidence"] == 55
    saved = store.get_signals()
    assert len(saved) == 1
    assert saved[0]["action"] == "HOLD"
    assert any(
        tool["function"]["name"] == "deliver_signal" for tool in client.requests[0][1]
    )


@pytest.mark.anyio
async def test_invalid_signal_rejected():
    db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    store = MemoryStore(db)
    bad = {
        "action": "MAYBE",
        "symbol": "SOL",
        "confidence": 200,
        "risk_level": "medium",
        "headline": "x",
        "rationale": ["x"],
        "beginner_explanation": "x",
        "disclaimer": "educational",
    }
    client = FakeChatClient(
        [
            AssistantReply(content="", tool_calls=(ToolCall("c1", "deliver_signal", bad),)),
            AssistantReply(content="Let me retry.", tool_calls=()),
        ]
    )
    coach = CoachAgent(client, store)
    agent = await coach.build(StubMCPManager())

    result = await coach.run(agent, [{"role": "user", "content": "recommend"}])

    assert result["signal"] is None
    assert store.get_signals() == []


@needs_model
@pytest.mark.anyio
async def test_live_signal_with_cost_basis_and_disclaimer():
    from app.config import Settings
    from app.llm import OpenAICompatClient

    db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    store = MemoryStore(db)
    store.set_risk_profile("risk_appetite", "moderate")
    store.set_risk_profile("goal", "long-term growth")
    store.commit()

    settings = Settings(
        llm_base_url=os.environ["LLM_BASE_URL"],
        llm_model=os.environ["LLM_MODEL"],
        llm_api_key=os.environ["LLM_API_KEY"],
    )
    coach = CoachAgent(OpenAICompatClient(settings), store)
    agent = await coach.build(StubMCPManager(), beginner_mode=True)

    result = await coach.run(
        agent,
        [
            {"role": "user", "content": "Should I sell my SOL right now? Give me a signal."}
        ],
    )

    signal = result["signal"]
    assert signal is not None, f"no signal delivered; content: {result['content'][:300]}"
    assert signal["action"] in {"BUY", "SELL", "HOLD"}
    assert signal["symbol"].upper().startswith("SOL")
    assert 0 <= signal["confidence"] <= 100
    assert signal["risk_level"] in {"low", "medium", "high"}
    assert signal["disclaimer"]
    assert result["tool_trace"], "agent should have consulted ticker or cost basis"
    stored = store.get_signals()
    assert stored and stored[0]["headline"] == signal["headline"]

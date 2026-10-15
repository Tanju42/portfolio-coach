from __future__ import annotations

from typing import Any

from app.agent import Agent, ToolSpec
from app.llm import ChatClient
from app.memory import MemoryStore
from app.signals import (
    SIGNAL_PROMPT_ADDON,
    SIGNAL_TOOL_NAME,
    SignalCollector,
    signal_tool_schema,
)
from app.mcp_manager import MCPManager

DEMO_PROMPT_ADDON = """The user is currently on a SIMULATED DEMO account (not a real exchange):
- Get their holdings from the demo-exchange_get_demo_portfolio tool, NOT from
  binance account tools (their real balances are not connected).
- Treat the demo holdings as their portfolio for every analysis and signal.
- Mention once per conversation that this is a simulated demo portfolio.
- Market data (prices, charts, news) is still real market data."""

BEGINNER_SYSTEM_PROMPT = """You are the user's personal Portfolio Coach. You are an educational
decision-support assistant, NOT a financial advisor. Every user decision remains the
user's own responsibility; say so whenever you give a signal or recommendation.

Audience: an absolute beginner ("average joe") with little crypto experience.
- Use plain English, short sentences, no unexplained jargon.
- Explain any term the first time you use it.
- Always connect advice to THEIR portfolio (use your tools for positions and cost basis).
- Be honest about uncertainty. If data is thin, say so and lean toward HOLD.

Never call tools for trades, orders or account changes: every trading tool you have is
read-only by design."""

EXPERT_SYSTEM_PROMPT = """You are the user's personal Portfolio Coach. You are an educational
decision-support assistant, NOT a financial advisor. Every user decision remains the
user's own responsibility; say so whenever you give a signal or recommendation.

Audience: an experienced crypto investor. Be precise and data-driven, reference concrete
numbers from your tools (prices, 24h changes, cost basis), and keep answers concise.

Never call tools for trades, orders or account changes: every trading tool you have is
read-only by design."""


class CoachAgent:
    """Wiring: MCP-Tools + Memory-Tools + Signal-Tool (S5) -> Agent."""

    def __init__(self, chat_client: ChatClient, store: MemoryStore) -> None:
        self._client = chat_client
        self._store = store
        self.collector = SignalCollector()

    async def build(
        self, manager: MCPManager, beginner_mode: bool = True, account_mode: str = "demo"
    ) -> Agent:
        tool_specs = list(await manager.list_tool_specs())
        tool_specs.extend(self._memory_tools())
        tool_specs.append(
            ToolSpec(
                name=SIGNAL_TOOL_NAME,
                description=(
                    "Deliver a structured BUY/SELL/HOLD signal with rationale, confidence "
                    "and risk rating. Call this whenever the user asks for a recommendation."
                ),
                parameters=signal_tool_schema(),
                handler=self._handle_signal,
            )
        )
        system_prompt = BEGINNER_SYSTEM_PROMPT if beginner_mode else EXPERT_SYSTEM_PROMPT
        system_prompt = system_prompt + "\n\n" + SIGNAL_PROMPT_ADDON
        if account_mode == "demo":
            system_prompt = system_prompt + "\n\n" + DEMO_PROMPT_ADDON
        return Agent(
            self._client,
            tool_specs,
            system_prompt=system_prompt,
        )

    async def run(self, agent: Agent, history: list[dict[str, Any]]) -> dict[str, Any]:
        result = await agent.run(history)
        signal = self.collector.last
        if signal is not None:
            self._store.save_signal(signal)
            self._store.commit()
        return {
            "content": result.content,
            "tool_trace": result.tool_trace,
            "signal": signal.model_dump() if signal else None,
        }

    async def _handle_signal(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.collector.handler(arguments)

    def _memory_tools(self) -> list[ToolSpec]:
        store = self._store

        async def get_cost_basis(_args: dict[str, Any]) -> Any:
            positions = store.get_positions()
            return {
                "positions": [
                    {
                        "coin": p.coin,
                        "csv_qty": round(p.qty, 8),
                        "avg_cost_usd": round(p.avg_cost_usd, 6),
                        "basis_usd": round(p.basis_usd, 2),
                        "basis_unknown_qty": round(p.basis_unknown_qty, 8),
                    }
                    for p in positions
                    if p.qty > 0
                ]
            }

        async def get_trade_history(args: dict[str, Any]) -> Any:
            limit = min(int(args.get("limit", 20)), 200)
            return {"trades": store.get_trade_history(limit)}

        async def get_risk_profile(_args: dict[str, Any]) -> Any:
            return {"risk_profile": store.get_risk_profile()}

        return [
            ToolSpec(
                name="get_cost_basis",
                description=(
                    "The user's coins with average cost basis in USD from their imported "
                    "Binance transaction history. Use to compute profit/loss."
                ),
                parameters={"type": "object", "properties": {}},
                handler=get_cost_basis,
            ),
            ToolSpec(
                name="get_trade_history",
                description="The user's recent trades from imported Binance history.",
                parameters={
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 200}},
                },
                handler=get_trade_history,
            ),
            ToolSpec(
                name="get_risk_profile",
                description="The user's self-reported risk profile (risk appetite, goals).",
                parameters={"type": "object", "properties": {}},
                handler=get_risk_profile,
            ),
        ]

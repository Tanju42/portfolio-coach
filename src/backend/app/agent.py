from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.llm import AssistantReply, ChatClient, ToolCall

SYSTEM_PROMPT = """You are the user's personal Portfolio Coach. You are an educational
decision-support assistant, NOT a financial advisor. Every user decision remains the
user's own responsibility; say so whenever you give a signal or recommendation.

You help a beginner ("average joe") investor:
1. Answer questions about their portfolio, markets and tracked topics using your tools.
2. Research current market topics with the news and market-data tools you have.
3. When asked for a signal, deliver a structured signal (BUY / SELL / HOLD) with a short
   rationale, a confidence level and a risk rating (low / medium / high).
4. Keep your language simple and jargon-free; explain terms on first use.

Never call tools for trades, orders or account changes: every trading tool you have is
read-only by design."""

ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def as_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class Agent:
    def __init__(
        self,
        chat_client: ChatClient,
        tools: list[ToolSpec],
        system_prompt: str = SYSTEM_PROMPT,
        max_tool_rounds: int = 12,
    ) -> None:
        self._client = chat_client
        self._tools = {spec.name: spec for spec in tools}
        self._system_prompt = system_prompt
        self._max_tool_rounds = max_tool_rounds

    async def run(self, history: list[dict[str, Any]]) -> AgentResult:
        messages: list[dict[str, Any]] = [{"role": "system", "content": self._system_prompt}]
        messages.extend(history)
        tool_trace: list[dict[str, Any]] = []
        for _ in range(self._max_tool_rounds):
            reply = await self._client.complete(messages, self._tool_specs())
            if not reply.tool_calls:
                return AgentResult(content=reply.content, tool_trace=tool_trace)
            messages.append(self._assistant_message(reply))
            for call in reply.tool_calls:
                result = await self._invoke(call)
                tool_trace.append({"name": call.name, "arguments": call.arguments, "result": result})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.call_id,
                        "content": _to_json(result),
                    }
                )
        raise AgentLoopError("max tool rounds exceeded")

    def _tool_specs(self) -> list[dict[str, Any]]:
        return [spec.as_openai_tool() for spec in self._tools.values()]

    async def _invoke(self, call: ToolCall) -> Any:
        spec = self._tools.get(call.name)
        if spec is None:
            return {"error": f"unknown tool: {call.name}"}
        try:
            return await spec.handler(call.arguments)
        except Exception as error:
            return {"error": str(error)}

    @staticmethod
    def _assistant_message(reply: AssistantReply) -> dict[str, Any]:
        message: dict[str, Any] = {"role": "assistant", "content": reply.content or None}
        if reply.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.call_id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in reply.tool_calls
            ]
        return message


@dataclass(frozen=True)
class AgentResult:
    content: str
    tool_trace: list[dict[str, Any]]


class AgentLoopError(RuntimeError):
    pass


def _to_json(value: Any) -> str:
    return json.dumps(value, default=str)

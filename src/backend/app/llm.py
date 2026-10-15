from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from openai import AsyncOpenAI

from app.config import Settings


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AssistantReply:
    content: str
    tool_calls: tuple[ToolCall, ...]


class ChatClient(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantReply: ...


class OpenAICompatClient:
    """Token Factory, Infernix und andere OpenAI-Dialekte (ADR-003)."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.llm_model
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.request_timeout,
        )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantReply:
        kwargs: dict[str, Any] = {"model": self._model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        response = await self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        calls = tuple(
            ToolCall(
                call_id=call.id,
                name=call.function.name,
                arguments=_parse_arguments(call.function.arguments),
            )
            for call in (message.tool_calls or [])
        )
        return AssistantReply(content=message.content or "", tool_calls=calls)


def _parse_arguments(raw: str) -> dict[str, Any]:
    import json

    if not raw:
        return {}
    return json.loads(raw)

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

KNOWLEDGE_TOOL_NAME = "deliver_knowledge"


class Knowledge(BaseModel):
    topic: str
    summary: str = Field(min_length=1)
    key_points: list[str]
    sources: list[dict[str, str]]
    confidence: Literal["low", "medium", "high"] = "medium"


def knowledge_tool_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Short topic label, e.g. 'NVIDIA outlook'"},
            "summary": {
                "type": "string",
                "description": "2-4 sentence plain-language summary for a beginner investor.",
            },
            "key_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 short bullet points with the most important facts.",
            },
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "url": {"type": "string"}},
                    "required": ["title", "url"],
                },
                "description": "Where the information came from (tool names count as sources too).",
            },
            "confidence": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "How solid the evidence is. Low if only one source or search failed.",
            },
        },
        "required": ["topic", "summary", "key_points", "sources", "confidence"],
    }


RESEARCH_SYSTEM_PROMPT = """You are a portfolio research assistant. Your research topic:
"{topic}"

Research this topic for a beginner investor ("average joe"):
1. Use search_web to find current information; use fetch_page on promising results.
2. Cross-check with market-data tools (stocks quote/history, crypto tickers, news) where relevant.
3. Then call the deliver_knowledge tool ONCE with a structured insight.

Rules:
- Cite every important claim to a source (title + url).
- If web search fails or returns little, fall back to market data and news tools,
  and set confidence to "low".
- Keep the summary plain and jargon-free; explain terms on first use.
- This is educational support, not financial advice; the user decides."""


class KnowledgeCollector:
    def __init__(self) -> None:
        self.knowledge: list[Knowledge] = []

    def handler(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            item = Knowledge.model_validate(arguments)
        except Exception as error:
            return {"accepted": False, "error": str(error)}
        self.knowledge.append(item)
        return {"accepted": True, "knowledge": item.model_dump()}

    @property
    def last(self) -> Knowledge | None:
        return self.knowledge[-1] if self.knowledge else None

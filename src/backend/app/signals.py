from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DISCLAIMER = (
    "This is educational support, not financial advice. Every trading decision is yours."
)

SIGNAL_TOOL_NAME = "deliver_signal"


class Signal(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    symbol: str
    confidence: int = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    headline: str
    rationale: list[str]
    beginner_explanation: str
    disclaimer: str = DISCLAIMER


def signal_tool_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["BUY", "SELL", "HOLD"],
                "description": "The trading signal for the user.",
            },
            "symbol": {"type": "string", "description": "Affected asset, e.g. SOL or BTCUSDT."},
            "confidence": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Confidence in this signal, 0-100.",
            },
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "How risky following this signal is.",
            },
            "headline": {"type": "string", "description": "One-sentence summary of the signal."},
            "rationale": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 short reasons supporting the signal.",
            },
            "beginner_explanation": {
                "type": "string",
                "description": "Plain-language explanation for a beginner investor, jargon-free.",
            },
            "disclaimer": {
                "type": "string",
                "description": "Must be included verbatim.",
            },
        },
        "required": [
            "action", "symbol", "confidence", "risk_level",
            "headline", "rationale", "beginner_explanation", "disclaimer",
        ],
    }


SIGNAL_PROMPT_ADDON = f"""When the user asks for a recommendation, buy/sell decision, or what they
should do with an asset, you MUST call the {SIGNAL_TOOL_NAME} tool with the structured
signal and then briefly confirm it in your answer. Decide BUY / SELL / HOLD based on the
user's risk profile, their positions and the market data your tools provide. If the data
does not support a clear decision, return HOLD. Keep confidence honest — do not inflate it.
Always use disclaimer: "{DISCLAIMER}"""


class SignalCollector:
    """Sammelt Signale aus deliver_signal-Tool-Calls (kombinierbar mit Session-Historie)."""

    def __init__(self) -> None:
        self.signals: list[Signal] = []

    def handler(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            signal = Signal.model_validate(arguments)
        except Exception as error:
            return {"accepted": False, "error": str(error)}
        self.signals.append(signal)
        return {"accepted": True, "signal": signal.model_dump()}

    @property
    def last(self) -> Signal | None:
        return self.signals[-1] if self.signals else None

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    request_timeout: float = 120.0
    max_tool_rounds: int = 12


def load_settings() -> Settings:
    missing = [
        name
        for name in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(f"missing env vars: {', '.join(missing)}")
    return Settings(
        llm_base_url=os.environ["LLM_BASE_URL"].rstrip("/"),
        llm_model=os.environ["LLM_MODEL"],
        llm_api_key=os.environ["LLM_API_KEY"],
    )

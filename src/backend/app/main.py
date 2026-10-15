from __future__ import annotations

import json
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.binance_csv import import_binance_csv
from app.config import Settings, load_settings
from app.coach import CoachAgent
from app.llm import OpenAICompatClient
from app.mcp_manager import MCPManager, load_server_configs
from app.memory import MemoryStore

DB_PATH = Path(__file__).resolve().parent.parent / "portfolio.db"

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = load_settings()
    store = MemoryStore(DB_PATH)
    manager = MCPManager(load_server_configs(Path(__file__).resolve().parent.parent / "servers" / "mcp_servers.json"))
    await manager.start()
    coach = CoachAgent(OpenAICompatClient(settings), store)
    agents = {mode: await coach.build(manager, beginner_mode=mode) for mode in (True, False)}
    state["store"] = store
    state["coach"] = coach
    state["agents"] = agents
    state["manager"] = manager
    try:
        yield
    finally:
        await manager.stop()


app = FastAPI(title="Portfolio Coach", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    beginner_mode: bool = True


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": "config-driven (LLM_BASE_URL/LLM_MODEL)"}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    store: MemoryStore = state["store"]
    store.add_chat_message(request.session_id, "user", request.message)
    history = store.get_chat_history(request.session_id)
    result = await state["coach"].run(state["agents"][request.beginner_mode], history)
    store.add_chat_message(request.session_id, "assistant", result["content"])
    store.commit()
    return {
        "content": result["content"],
        "signal": result["signal"],
        "tools_used": [t["name"] for t in result["tool_trace"]],
    }


@app.get("/api/signals")
def signals() -> dict:
    return {"signals": state["store"].get_signals()}


@app.get("/api/portfolio")
async def portfolio() -> dict:
    store: MemoryStore = state["store"]
    positions = {p.coin: p for p in store.get_positions()}
    from app.portfolio import build_portfolio

    return await build_portfolio(state["manager"], positions, "binance_get_account_assets", "binance_get_ticker")


@app.get("/api/import/help")
def import_help() -> dict:
    return {
        "steps": [
            "Log in at binance.com and open your profile: Profile & Preferences.",
            "Go to 'Account' -> 'Transaction History' (or binance.com/en/my/wallet/account/transaction-history).",
            "Set the period to 'All time' and the account to 'Spot'.",
            "Click 'Generate Report' (or the export icon) and choose CSV.",
            "Download the file and upload it here. Nothing leaves your machine: the "
            "parser runs locally and only stores positions and trades in the local SQLite DB.",
        ],
        "expected_columns": ["User ID", "Time", "Account", "Operation", "Coin", "Change", "Remark"],
        "notes": [
            "Re-uploading the same file is safe: imports are idempotent.",
            "Cost basis uses the average-cost method in USD (EUR counted at ~1.10 USD).",
            "Coins you acquired via Auto-Invest plans may show as 'unknown basis' — "
            "the report tells you exactly how much.",
        ],
    }


@app.post("/api/import/csv")
async def import_csv(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")
    tmp = Path(tempfile.NamedTemporaryFile(suffix=".csv", delete=False).name)
    try:
        with tmp.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        store: MemoryStore = state["store"]
        summary = import_binance_csv(tmp, store, source_name=file.filename)
    finally:
        tmp.unlink(missing_ok=True)
    return {"imported": True, "file": file.filename, "summary": summary.as_dict()}

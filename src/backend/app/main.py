from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

import os

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
SERVERS_PATH = Path(__file__).resolve().parent.parent / "servers" / "mcp_servers.json"

LIVE_ACCOUNT_TOOL = "binance_get_account_assets"
DEMO_ACCOUNT_TOOL = "demo-exchange_get_demo_portfolio"
MARKET_TOOLS = [
    "coingecko_get_fear_greed",
    "coingecko_get_global_market",
    "coingecko_get_top_movers",
    "coingecko_get_news",
]

state: dict = {}
_market_cache: dict = {"ts": 0.0, "data": None}


async def _rebuild_agents(account_mode: str) -> dict:
    coach: CoachAgent = state["coach"]
    agents = {}
    for beginner_mode in (True, False):
        agents[beginner_mode] = await coach.build(
            state["manager"], beginner_mode=beginner_mode, account_mode=account_mode
        )
    return agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = load_settings()
    store = MemoryStore(DB_PATH)
    manager = MCPManager(load_server_configs(SERVERS_PATH))
    await manager.start()
    coach = CoachAgent(OpenAICompatClient(settings), store)
    state["store"] = store
    state["coach"] = coach
    state["manager"] = manager
    account_mode = store.get_setting("account_mode", "demo")
    state["account_mode"] = account_mode
    state["agents"] = await _rebuild_agents(account_mode)
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


class ModeRequest(BaseModel):
    mode: str


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


@app.get("/api/settings")
def get_settings_view() -> dict:
    return {
        "account_mode": state["account_mode"],
        "has_live_keys": bool(os.environ.get("BINANCE_API_KEY")),
    }


@app.post("/api/settings/mode")
async def set_account_mode(request: ModeRequest) -> dict:
    if request.mode not in ("demo", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'demo' or 'live'")
    if request.mode == "live" and not os.environ.get("BINANCE_API_KEY"):
        raise HTTPException(status_code=400, detail="Binance API keys not configured in backend .env")
    state["account_mode"] = request.mode
    state["store"].set_setting("account_mode", request.mode)
    state["agents"] = await _rebuild_agents(request.mode)
    return {"account_mode": request.mode, "has_live_keys": bool(os.environ.get("BINANCE_API_KEY"))}


@app.get("/api/market")
async def market() -> dict:
    now = time.time()
    if _market_cache["data"] is not None and now - _market_cache["ts"] < 60:
        return _market_cache["data"]
    specs = {spec.name: spec for spec in await state["manager"].list_tool_specs()}
    missing = [name for name in MARKET_TOOLS if name not in specs]
    if missing:
        return {"error": f"market tools unavailable: {missing}"}

    async def call(name: str):
        result = await specs[name].handler({})
        try:
            return json.loads(result["content"][0]["text"])
        except (KeyError, IndexError, json.JSONDecodeError):
            return {"error": f"{name} returned unparseable content"}

    fear_greed, global_market, movers, news = await asyncio.gather(
        *(call(name) for name in MARKET_TOOLS)
    )
    data = {
        "fear_greed": fear_greed,
        "global": global_market,
        "movers": movers,
        "news": news,
        "fetched_at": int(now),
    }
    _market_cache["ts"] = now
    _market_cache["data"] = data
    return data


@app.get("/api/portfolio")
async def portfolio() -> dict:
    store: MemoryStore = state["store"]
    positions = {p.coin: p for p in store.get_positions()}
    from app.portfolio import build_portfolio

    if state["account_mode"] == "live":
        result = await build_portfolio(state["manager"], positions, LIVE_ACCOUNT_TOOL, "binance_get_ticker")
        if "error" not in result:
            return result
    return await build_portfolio(state["manager"], positions, DEMO_ACCOUNT_TOOL, "binance_get_ticker")


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

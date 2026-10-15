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


@app.get("/api/portfolios")
async def portfolios_all() -> dict:
    store: MemoryStore = state["store"]
    positions = {p.coin: p for p in store.get_positions()}
    from app.portfolios import build_all_portfolios, record_snapshots

    result = await build_all_portfolios(state["manager"], positions, state["account_mode"])
    record_snapshots(store, result)
    configured = [c.name for c in state["manager"]._configs]
    connected = set(state["manager"].connected_names())
    result["providers"] = [
        {"name": name, "connected": name in connected} for name in configured
    ]
    return result


@app.get("/api/portfolio")
async def portfolio() -> dict:
    store: MemoryStore = state["store"]
    positions = {p.coin: p for p in store.get_positions()}
    from app.portfolios import build_all_portfolios

    result = await build_all_portfolios(state["manager"], positions, state["account_mode"])
    totals = result["totals"]
    return {
        "rows": result["rows"],
        "total_value_usd": totals["total_value_usd"],
        "total_cost_usd": totals["total_cost_usd"],
        "total_pnl_usd": totals["total_pnl_usd"],
        "portfolios": result["portfolios"],
        "note": "Aggregated across all connected portfolios. Cost basis from imported transaction history (average-cost method).",
    }


@app.get("/api/portfolio/history")
async def portfolio_history(range: str = "7d") -> dict:
    from app.portfolios import history_series

    return history_series(state["store"], range)


@app.get("/api/asset/{asset}")
async def asset_detail(asset: str) -> dict:
    store: MemoryStore = state["store"]
    positions = {p.coin: p for p in store.get_positions()}
    from app.portfolios import build_all_portfolios

    result = await build_all_portfolios(state["manager"], positions, state["account_mode"])
    target = asset.strip().upper()
    row = next((r for r in result["rows"] if r["asset"].upper() == target), None)
    if row is None:
        raise HTTPException(status_code=404, detail=f"asset {target} not in any connected portfolio")

    specs = {spec.name: spec for spec in await state["manager"].list_tool_specs()}
    kind = "stocks" if any("Broker" in p["label"] for p in row["providers"]) else "crypto"
    sparkline = []
    try:
        if kind == "stocks" and "stocks_get_history" in specs:
            data = await _call_tool(specs["stocks_get_history"], {"ticker": target, "period": "1mo"})
            sparkline = [
                {"t": point["date"], "close": float(point["close"])} for point in data.get("points", [])
            ]
        elif "binance_get_klines" in specs:
            data = await _call_tool(
                specs["binance_get_klines"], {"symbol": f"{target}USDT", "interval": "1d", "limit": 30}
            )
            sparkline = [
                {"t": candle["open_time"], "close": float(candle["close"])}
                for candle in data.get("candles", [])
            ]
    except Exception:
        sparkline = []

    signals = [
        s for s in store.get_signals(50)
        if target in s["symbol"].upper() or s["symbol"].upper() in target
    ][:5]
    knowledge = [
        k for k in store.get_knowledge(50) if target.lower() in k["topic"].lower()
    ][:5]
    return {
        "asset": row["asset"],
        "kind": kind,
        "qty": row["qty"],
        "price_usd": _current_price(result, target),
        "value_usd": row["value_usd"],
        "avg_cost_usd": row["avg_cost_usd"],
        "pnl_usd": row["pnl_usd"],
        "basis_reliable_share": row["basis_reliable_share"],
        "providers": row["providers"],
        "sparkline": sparkline,
        "signals": signals,
        "knowledge": knowledge,
    }


def _current_price(result: dict, target: str) -> float | None:
    for block in result["portfolios"]:
        if block.get("status") != "ok":
            continue
        for block_row in block.get("rows", []):
            if block_row["asset"].upper() == target and block_row["price_usd"]:
                return block_row["price_usd"]
    return None


async def _call_tool(spec, arguments: dict) -> dict:
    import json as _json

    result = await spec.handler(arguments)
    return _json.loads(result["content"][0]["text"])


@app.get("/api/allocation")
async def allocation() -> dict:
    store: MemoryStore = state["store"]
    positions = {p.coin: p for p in store.get_positions()}
    from app.analytics import rebalance_suggestions
    from app.portfolios import build_all_portfolios

    result = await build_all_portfolios(state["manager"], positions, state["account_mode"])
    targets = store.get_allocation_targets()
    suggestions = rebalance_suggestions(result["rows"], targets)
    return {
        "targets": targets or None,
        **suggestions,
        "total_value_usd": result["totals"]["total_value_usd"],
    }


class AllocationRequest(BaseModel):
    targets: dict[str, float]


@app.post("/api/allocation")
async def set_allocation(request: AllocationRequest) -> dict:
    if not request.targets:
        raise HTTPException(status_code=400, detail="targets must not be empty")
    total = sum(request.targets.values())
    if total <= 0:
        raise HTTPException(status_code=400, detail="targets must sum to a positive value")
    state["store"].set_allocation_targets({k.upper(): float(v) for k, v in request.targets.items()})
    state["store"].commit()
    return {"saved": True, "targets": {k.upper(): v for k, v in request.targets.items()}}


@app.get("/api/risk")
async def risk() -> dict:
    positions = {p.coin: p for p in state["store"].get_positions()}
    from app.analytics import risk_report
    from app.portfolios import build_all_portfolios

    result = await build_all_portfolios(state["manager"], positions, state["account_mode"])
    return risk_report(result["rows"], result["portfolios"])


@app.get("/api/watchlist")
async def watchlist_get() -> dict:
    store: MemoryStore = state["store"]
    items = store.get_watchlist()
    specs = {spec.name: spec for spec in await state["manager"].list_tool_specs()}
    for item in items:
        item["price_usd"] = None
        item["change_24h_pct"] = None
        try:
            if item["kind"] == "stocks" and "stocks_get_quote" in specs:
                data = await _call_tool(specs["stocks_get_quote"], {"ticker": item["symbol"]})
                item["price_usd"] = data.get("price")
                item["change_24h_pct"] = data.get("change_pct")
            elif "binance_get_ticker" in specs:
                data = await _call_tool(specs["binance_get_ticker"], {"symbol": f"{item['symbol']}USDT"})
                if "error" not in data:
                    item["price_usd"] = float(data.get("last_price", 0)) or None
                    item["change_24h_pct"] = float(data.get("price_change_percent_24h", 0)) or None
        except Exception:
            pass
    return {"watchlist": items}


class WatchRequest(BaseModel):
    symbol: str
    kind: str = "crypto"


@app.post("/api/watchlist")
async def watchlist_add(request: WatchRequest) -> dict:
    symbol = request.symbol.strip().upper()
    if not symbol or len(symbol) > 24:
        raise HTTPException(status_code=400, detail="symbol must be 1-24 characters")
    if request.kind not in ("crypto", "stocks"):
        raise HTTPException(status_code=400, detail="kind must be 'crypto' or 'stocks'")
    added = state["store"].add_watch(symbol, request.kind)
    state["store"].commit()
    return {"added": added, "symbol": symbol, "kind": request.kind}


@app.delete("/api/watchlist/{symbol}")
async def watchlist_remove(symbol: str) -> dict:
    removed = state["store"].remove_watch(symbol.strip().upper())
    state["store"].commit()
    return {"removed": removed, "symbol": symbol.strip().upper()}


class ResearchRequest(BaseModel):
    topic: str


@app.get("/api/knowledge")
def knowledge_list() -> dict:
    return {"knowledge": state["store"].get_knowledge()}


@app.post("/api/knowledge/research")
async def knowledge_research(request: ResearchRequest) -> dict:
    topic = request.topic.strip()
    if not topic or len(topic) > 200:
        raise HTTPException(status_code=400, detail="topic must be 1-200 characters")
    coach: CoachAgent = state["coach"]
    agent = await coach.build_research_agent(state["manager"], topic)
    result = await coach.run_research(agent, topic)
    return {"topic": topic, **result}


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

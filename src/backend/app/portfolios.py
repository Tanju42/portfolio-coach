from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.mcp_manager import MCPManager

SNAPSHOT_THROTTLE_SECONDS = 300
STABLES = {"USDC", "USDT", "FDUSD", "BUSD"}
PRICE_CONCURRENCY = 3

ACCOUNT_SOURCES = [
    {
        "provider": "demo-exchange",
        "tool": "get_demo_portfolio",
        "label": "Demo Crypto Exchange",
        "kind": "crypto",
        "requires_live": False,
    },
    {
        "provider": "demo-exchange",
        "tool": "get_demo_broker_portfolio",
        "label": "Demo Brokerage",
        "kind": "stocks",
        "requires_live": False,
    },
    {
        "provider": "binance",
        "tool": "get_account_assets",
        "label": "Binance Live",
        "kind": "crypto",
        "requires_live": True,
    },
]


def _base_asset(asset: str) -> str:
    return asset[2:] if asset.startswith("LD") else asset


def _price_tool(kind: str) -> tuple[str, str]:
    if kind == "stocks":
        return "stocks_get_quote", "ticker"
    return "binance_get_ticker", "symbol"


async def _call_json(handler, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    result = await handler(arguments or {})
    return json.loads(result["content"][0]["text"])


def _fetch_prices_of(kind: str, assets: list[str], specs: dict[str, Any], sem: asyncio.Semaphore):
    tool_name, arg_name = _price_tool(kind)
    tool = specs.get(tool_name)
    cache: dict[str, dict[str, Any]] = {}

    async def fetch(asset: str) -> dict[str, Any]:
        if asset in cache:
            return cache[asset]
        if tool is None:
            return {"error": f"{tool_name} unavailable"}
        async with sem:
            try:
                data = await _call_json(tool.handler, {arg_name: asset})
            except Exception as error:
                data = {"error": str(error)[:120]}
        cache[asset] = data
        return data

    return fetch


async def _build_one(
    source: dict[str, Any],
    specs: dict[str, Any],
    positions: dict[str, Any],
) -> dict[str, Any]:
    spec = specs.get(f"{source['provider']}_{source['tool']}")
    if spec is None:
        return {"provider": source["provider"], "label": source["label"], "kind": source["kind"],
                "status": "error", "error": f"{source['tool']} not available"}

    account = await _call_json(spec.handler)
    if "error" in account:
        return {"provider": source["provider"], "label": source["label"], "kind": source["kind"],
                "status": "error", "error": account["error"]}

    holdings = {
        entry["asset"]: (entry["free"] + entry["locked"], entry.get("avg_cost_usd"))
        for entry in account.get("balances", [])
        if entry["free"] + entry["locked"] > 1e-9
    }
    kind = source["kind"]
    fetch_price = _fetch_prices_of(kind, sorted(holdings), specs, asyncio.Semaphore(PRICE_CONCURRENCY))

    async def fetch(asset: str) -> dict[str, Any]:
        if kind == "crypto":
            return await fetch_price(f"{_base_asset(asset)}USDT")
        return await fetch_price(asset)

    price_results = await asyncio.gather(*(fetch(asset) for asset in holdings))

    rows = []
    for (asset, (qty, provider_cost)), price_data in zip(holdings.items(), price_results):
        base = _base_asset(asset)
        price = float(price_data.get("price", 0.0) or price_data.get("last_price", 0.0) or 0.0)
        change_pct = price_data.get("change_pct")
        if change_pct is None:
            change_pct = price_data.get("price_change_percent_24h")
        position = positions.get(base)
        if position is not None and position.qty > 0:
            avg_cost = position.avg_cost_usd
            reliable_share = 1 - (position.basis_unknown_qty / position.qty)
        elif provider_cost is not None:
            avg_cost = float(provider_cost)
            reliable_share = 1.0
        else:
            avg_cost, reliable_share = None, 0.0
        cost = avg_cost * qty if avg_cost is not None else 0.0
        rows.append({
            "asset": base,
            "raw_asset": asset,
            "qty": qty,
            "price_usd": price,
            "value_usd": round(price * qty, 2),
            "avg_cost_usd": avg_cost,
            "cost_usd": round(cost, 2),
            "pnl_usd": round(price * qty - cost, 2),
            "basis_reliable_share": round(reliable_share, 2),
            "change_24h_pct": float(change_pct) if change_pct is not None else None,
            "price_error": price_data.get("error"),
        })

    rows.sort(key=lambda row: -row["value_usd"])
    total_value = sum(row["value_usd"] for row in rows)
    total_cost = sum(row["cost_usd"] for row in rows)
    return {
        "provider": source["provider"],
        "label": source["label"],
        "kind": kind,
        "status": "ok",
        "account_type": account.get("account_type", "UNKNOWN"),
        "note": account.get("note"),
        "asset_count": len(rows),
        "rows": rows,
        "total_value_usd": round(total_value, 2),
        "total_cost_usd": round(total_cost, 2),
        "total_pnl_usd": round(total_value - total_cost, 2),
    }


def merge_rows(portfolio_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for block in portfolio_blocks:
        if block.get("status") != "ok":
            continue
        for row in block.get("rows", []):
            base = row["asset"]
            entry = grouped.setdefault(base, {
                "asset": base,
                "qty": 0.0,
                "value_usd": 0.0,
                "cost_usd": 0.0,
                "pnl_usd": 0.0,
                "providers": [],
                "basis_reliable_shares": [],
            })
            entry["qty"] += row["qty"]
            entry["value_usd"] += row["value_usd"]
            entry["cost_usd"] += row["cost_usd"]
            entry["pnl_usd"] += row["pnl_usd"]
            entry["basis_reliable_shares"].append((row["value_usd"], row["basis_reliable_share"]))
            if row["avg_cost_usd"] is not None:
                entry.setdefault("basis_values", []).append((row["value_usd"], row["avg_cost_usd"]))
            entry["providers"].append({
                "provider": block["provider"],
                "label": block["label"],
                "qty": row["qty"],
                "value_usd": row["value_usd"],
                "avg_cost_usd": row["avg_cost_usd"],
                "pnl_usd": row["pnl_usd"],
                "change_24h_pct": row.get("change_24h_pct"),
            })

    merged = []
    for entry in grouped.values():
        value = round(entry["value_usd"], 2)
        reliable_share = 0.0
        total_weighted = sum(w for w, _ in entry["basis_reliable_shares"])
        if total_weighted > 0:
            reliable_share = sum(w * s for w, s in entry["basis_reliable_shares"]) / total_weighted
        avg_cost = None
        if entry.get("basis_values"):
            total_basis_weight = sum(w for w, _ in entry["basis_values"])
            if total_basis_weight > 0:
                avg_cost = sum(w * c for w, c in entry["basis_values"]) / total_basis_weight
        change_24h = next(
            (p.get("change_24h_pct") for p in entry["providers"] if p.get("change_24h_pct") is not None),
            None,
        )
        merged.append({
            "asset": entry["asset"],
            "qty": round(entry["qty"], 8),
            "value_usd": value,
            "cost_usd": round(entry["cost_usd"], 2),
            "pnl_usd": round(entry["pnl_usd"], 2),
            "avg_cost_usd": round(avg_cost, 6) if avg_cost is not None else None,
            "basis_reliable_share": round(reliable_share, 2),
            "change_24h_pct": change_24h,
            "providers": entry["providers"],
        })
    merged.sort(key=lambda row: -row["value_usd"])
    return merged


async def build_all_portfolios(
    manager: MCPManager, positions: dict[str, Any], account_mode: str
) -> dict[str, Any]:
    specs = {spec.name: spec for spec in await manager.list_tool_specs()}
    active_sources = []
    for source in ACCOUNT_SOURCES:
        if source["requires_live"] and account_mode != "live":
            active_sources.append({
                "provider": source["provider"], "label": source["label"], "kind": source["kind"],
                "status": "not_connected", "error": "live keys not configured (use demo mode)",
                "asset_count": 0, "rows": [], "total_value_usd": 0.0,
                "total_cost_usd": 0.0, "total_pnl_usd": 0.0,
            })
        else:
            active_sources.append(source)

    async def safe_build(source: dict[str, Any]) -> dict[str, Any]:
        if source.get("status"):
            return source
        try:
            return await _build_one(source, specs, positions)
        except Exception as error:
            return {
                "provider": source["provider"], "label": source["label"], "kind": source["kind"],
                "status": "error", "error": f"{type(error).__name__}: {error}"[:200],
                "asset_count": 0, "rows": [], "total_value_usd": 0.0,
                "total_cost_usd": 0.0, "total_pnl_usd": 0.0,
            }

    portfolios = await asyncio.gather(*(safe_build(source) for source in active_sources))
    blocks = list(portfolios)
    ok_blocks = [block for block in blocks if block.get("status") == "ok"]
    rows = merge_rows(blocks)
    total_value = round(sum(block["total_value_usd"] for block in ok_blocks), 2)
    total_cost = round(sum(block["total_cost_usd"] for block in ok_blocks), 2)
    return {
        "portfolios": blocks,
        "rows": rows,
        "totals": {
            "total_value_usd": total_value,
            "total_cost_usd": total_cost,
            "total_pnl_usd": round(total_value - total_cost, 2),
            "portfolio_count": len(ok_blocks),
            "asset_count": len(rows),
        },
        "fetched_at": int(time.time()),
    }


def record_snapshots(store, result: dict[str, Any], now: int | None = None) -> int:
    now = int(time.time() if now is None else now)
    recorded = 0
    for block in result.get("portfolios", []):
        if block.get("status") != "ok" or block.get("total_value_usd", 0) <= 0:
            continue
        if block["provider"] == "binance" and block.get("account_type") == "LIVE":
            provider_key = "binance-live"
        else:
            provider_key = f"{block['provider']}:{block['label']}"
        latest = store.latest_snapshot_ts(provider_key)
        if latest is not None and now - latest < SNAPSHOT_THROTTLE_SECONDS:
            continue
        store.save_snapshot(
            ts=now,
            provider=provider_key,
            label=block.get("label", provider_key),
            total_value=block.get("total_value_usd", 0.0),
            total_cost=block.get("total_cost_usd"),
            pnl=block.get("total_pnl_usd"),
            asset_json=json.dumps(
                [{"asset": r["asset"], "value_usd": r["value_usd"]} for r in block.get("rows", [])]
            ),
        )
        recorded += 1
    if recorded:
        store.commit()
    return recorded


RANGE_SECONDS = {"24h": 86400, "7d": 7 * 86400, "all": None}


def history_series(store, range_str: str) -> dict[str, Any]:
    window = RANGE_SECONDS.get(range_str)
    now = int(time.time())
    since = None if window is None else now - window
    snapshots = store.get_snapshots(since_ts=since)
    if not snapshots:
        return {"range": range_str, "points": [], "collecting": True}
    by_ts: dict[int, float] = {}
    for snap in snapshots:
        by_ts[snap["ts"]] = by_ts.get(snap["ts"], 0.0) + (snap["total_value"] or 0.0)
    points = [{"ts": ts, "value_usd": round(value, 2)} for ts, value in sorted(by_ts.items())]
    return {
        "range": range_str,
        "points": points,
        "collecting": len(points) < 2,
        "first_ts": points[0]["ts"] if points else None,
        "last_ts": points[-1]["ts"] if points else None,
    }

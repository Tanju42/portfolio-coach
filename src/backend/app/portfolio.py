from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from app.mcp_manager import MCPManager

STABLES: dict[str, float] = {"USDC": 1.0, "USDT": 1.0, "FDUSD": 1.0, "BUSD": 1.0}
MAX_PRICE_CONCURRENCY = 3


@dataclass
class PortfolioRow:
    asset: str
    qty: float
    price_usd: float
    value_usd: float
    avg_cost_usd: float | None
    cost_usd: float
    pnl_usd: float
    basis_reliable_share: float


async def build_portfolio(
    manager: MCPManager, positions: dict[str, Any], account_tool_name: str, ticker_tool_name: str
) -> dict[str, Any]:
    specs = {spec.name: spec for spec in await manager.list_tool_specs()}
    account = specs.get(account_tool_name)
    ticker = specs.get(ticker_tool_name)
    if account is None or ticker is None:
        return {"error": "binance MCP server not running"}

    account_data = json.loads((await account.handler({}))["content"][0]["text"])
    if "error" in account_data:
        return {"error": account_data["error"]}

    holdings = {
        b["asset"]: (b["free"] + b["locked"], b.get("avg_cost_usd"))
        for b in account_data["balances"]
        if b["free"] + b["locked"] > 1e-9
    }

    sem = asyncio.Semaphore(MAX_PRICE_CONCURRENCY)
    cache: dict[str, float] = dict(STABLES)

    async def price_of(asset: str) -> float:
        if asset in cache:
            return cache[asset]
        base = asset[2:] if asset.startswith("LD") else asset
        symbol = f"{base}USDT"
        async with sem:
            result = await ticker.handler({"symbol": symbol})
        try:
            data = json.loads(result["content"][0]["text"])
            price = float(data.get("last_price", 0.0)) if "error" not in data else 0.0
        except (KeyError, IndexError, ValueError, json.JSONDecodeError):
            price = 0.0
        cache[asset] = price
        return price

    price_values = await asyncio.gather(*(price_of(a) for a in holdings))
    rows: list[PortfolioRow] = []
    for (asset, (qty, provider_cost)), price in zip(holdings.items(), price_values):
        base = asset[2:] if asset.startswith("LD") else asset
        position = positions.get(asset) or positions.get(base)
        if position is not None and position.qty > 0:
            avg_cost = position.avg_cost_usd
            reliable_share = 1 - (position.basis_unknown_qty / position.qty)
        elif provider_cost is not None:
            avg_cost = float(provider_cost)
            reliable_share = 1.0
        else:
            avg_cost, reliable_share = None, 0.0
        cost = avg_cost * qty if avg_cost is not None else 0.0
        value = price * qty
        rows.append(
            PortfolioRow(
                asset=asset,
                qty=qty,
                price_usd=price,
                value_usd=value,
                avg_cost_usd=avg_cost,
                cost_usd=cost,
                pnl_usd=value - cost,
                basis_reliable_share=reliable_share,
            )
        )
    rows.sort(key=lambda row: -row.value_usd)
    total_value = sum(row.value_usd for row in rows)
    total_cost = sum(row.cost_usd for row in rows)
    return {
        "rows": [
            {
                "asset": row.asset,
                "qty": row.qty,
                "price_usd": row.price_usd,
                "value_usd": round(row.value_usd, 2),
                "avg_cost_usd": round(row.avg_cost_usd, 6) if row.avg_cost_usd is not None else None,
                "cost_usd": round(row.cost_usd, 2),
                "pnl_usd": round(row.pnl_usd, 2),
                "basis_reliable_share": round(row.basis_reliable_share, 2),
            }
            for row in rows
        ],
        "total_value_usd": round(total_value, 2),
        "total_cost_usd": round(total_cost, 2),
        "total_pnl_usd": round(total_value - total_cost, 2),
        "note": "Cost basis is estimated from your imported Binance transaction history (average-cost method).",
    }

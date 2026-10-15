import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

import httpx
from mcp.server.mcpserver import MCPServer

BASE_URL = "https://api.binance.com"

mcp = MCPServer("binance")


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(f"{BASE_URL}{path}", params=params)
        if response.status_code >= 400:
            return {"error": f"binance api {response.status_code}: {response.text[:200]}"}
        return response.json()


def _signed_get(path: str, params: dict) -> dict:
    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        return {
            "error": "Binance API keys not configured. Set BINANCE_API_KEY and "
            "BINANCE_API_SECRET (read-only permissions only) to see your account."
        }
    params = dict(params, timestamp=int(time.time() * 1000), recvWindow=5000)
    query = urlencode(params)
    signature = hmac.new(
        api_secret.encode(), query.encode(), hashlib.sha256
    ).hexdigest()
    headers = {"X-MBX-APIKEY": api_key}
    response = httpx.get(
        f"{BASE_URL}{path}?{query}&signature={signature}", headers=headers, timeout=15
    )
    if response.status_code >= 400:
        return {"error": f"binance api {response.status_code}: {response.text[:200]}"}
    return response.json()


@mcp.tool()
async def get_ticker(symbol: str) -> dict:
    """24h ticker for a trading pair, e.g. BTCUSDT. Shows price and 24h change."""
    data = await _get("/api/v3/ticker/24hr", {"symbol": symbol.upper()})
    if "error" in data:
        return data
    return {
        "symbol": data["symbol"],
        "last_price": data["lastPrice"],
        "price_change_percent_24h": data["priceChangePercent"],
        "high_24h": data["highPrice"],
        "low_24h": data["lowPrice"],
        "volume_24h": data["volume"],
    }


@mcp.tool()
async def get_klines(symbol: str, interval: str = "1d", limit: int = 14) -> dict:
    """OHLCV candles for a symbol. interval like 1h, 4h, 1d, 1w. Max 100 candles."""
    limit = min(int(limit), 100)
    data = await _get(
        "/api/v3/klines", {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    )
    if "error" in data:
        return data
    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "candles": [
            {
                "open_time": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
            }
            for row in data
        ],
    }


@mcp.tool()
async def get_book_ticker(symbol: str) -> dict:
    """Best bid and ask (order book top) for a trading pair."""
    data = await _get("/api/v3/ticker/bookTicker", {"symbol": symbol.upper()})
    return {"symbol": data["symbol"], "bid": data["bidPrice"], "ask": data["askPrice"]}


@mcp.tool()
def get_account_assets() -> dict:
    """Spot wallet balances (read-only). Requires read-only Binance API keys in env."""
    data = _signed_get("/api/v3/account", {})
    if "error" in data:
        return data
    balances = [
        {"asset": b["asset"], "free": float(b["free"]), "locked": float(b["locked"])}
        for b in data.get("balances", [])
        if float(b["free"]) > 0 or float(b["locked"]) > 0
    ]
    return {"account_type": data.get("accountType", "SPOT"), "balances": balances}


if __name__ == "__main__":
    mcp.run()

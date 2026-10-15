import hashlib
import math
import os
import time

import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("stocks")

AV_BASE = "https://www.alphavantage.co/query"
YAHOO = "https://query1.finance.yahoo.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

PERIOD_ROWS = {"1mo": 23, "3mo": 66, "6mo": 132, "1y": 260, "5y": 1250}

DEMO_BASE_PRICES = {
    "AAPL": 245.0, "MSFT": 505.0, "NVDA": 195.0, "KO": 72.0,
    "SAP.DE": 210.0, "AMZN": 245.0, "GOOGL": 310.0, "TSLA": 430.0,
    "META": 720.0, "NFLX": 1150.0, "AMD": 235.0, "INTC": 38.0,
}


def stooq_symbol(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if "." in ticker:
        return ticker.lower()
    return f"{ticker.lower()}.us"


def demo_price(ticker: str) -> dict:
    """Deterministic simulated price (DEMO): seeded walk around a base price, refreshed hourly."""
    ticker = ticker.strip().upper()
    seed_text = f"{ticker}-{time.strftime('%Y%m%d%H')}"
    seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:12], 16)
    base = DEMO_BASE_PRICES.get(ticker, 100.0 + (seed % 500))
    drift = ((seed >> 8) % 4000 - 2000) / 10000
    wave = math.sin((seed % 10000) / 780.0) * 0.04
    price = base * (1 + drift + wave)
    prev = base * (1 + drift)
    return {
        "ticker": ticker,
        "price": round(price, 2),
        "currency": "local",
        "change_pct": round((price / prev - 1) * 100, 2),
        "source": "DEMO simulated price (no live stock feed configured)",
        "live": False,
    }


async def yahoo_quote(ticker: str) -> dict | None:
    params = {"range": "1d", "interval": "1d"}
    async with httpx.AsyncClient(timeout=10, headers=HEADERS, follow_redirects=True) as client:
        response = await client.get(f"{YAHOO}/v8/finance/chart/{ticker.upper()}", params=params)
    if response.status_code != 200:
        return None
    result = (response.json().get("chart", {}).get("result") or [])
    if not result:
        return None
    meta = result[0].get("meta", {})
    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose")
    if not price:
        return None
    return {
        "ticker": ticker.upper(),
        "price": price,
        "currency": meta.get("currency", "USD"),
        "previous_close": prev,
        "change_pct": round((price / prev - 1) * 100, 2) if prev else None,
        "source": "Yahoo Finance (live)",
        "live": True,
    }


async def alphavantage_quote(ticker: str) -> dict | None:
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return None
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(
            AV_BASE, params={"function": "GLOBAL_QUOTE", "symbol": ticker.upper(), "apikey": api_key}
        )
    data = response.json().get("Global Quote", {})
    if not data:
        return None
    try:
        price = float(data["05. price"])
        prev = float(data["08. previous close"])
    except (KeyError, ValueError):
        return None
    return {
        "ticker": ticker.upper(),
        "price": price,
        "currency": "USD",
        "previous_close": prev,
        "change_pct": round((price / prev - 1) * 100, 2) if prev else None,
        "source": "Alpha Vantage (live)",
        "live": True,
    }


@mcp.tool()
async def get_quote(ticker: str) -> dict:
    """Quote for a stock ticker, e.g. AAPL, NVDA (US) or SAP.DE (German).
    Tries Alpha Vantage (if ALPHA_VANTAGE_API_KEY set), then Yahoo Finance, then a
    clearly-labeled simulated demo price."""
    ticker = ticker.strip().upper()
    for provider in (alphavantage_quote, yahoo_quote):
        try:
            result = await provider(ticker)
        except Exception:
            result = None
        if result:
            return result
    return demo_price(ticker)


@mcp.tool()
async def get_history(ticker: str, period: str = "6mo") -> dict:
    """Simulated daily close history for a ticker (DEMO). period: 1mo/3mo/6mo/1y/5y."""
    ticker = ticker.strip().upper()
    rows_n = PERIOD_ROWS.get(period, 132)
    points = []
    start_price = DEMO_BASE_PRICES.get(ticker, 100.0 + (int(hashlib.sha256(ticker.encode()).hexdigest()[:8], 16) % 500))
    daily_seed = int(hashlib.sha256(ticker.encode()).hexdigest()[:8], 16)
    price = start_price * 0.82
    for i in range(rows_n):
        step = ((daily_seed >> (i % 24)) % 1000 - 500) / 20000
        wave = math.sin(i / 13.0 + (daily_seed % 17)) * 0.006
        price = price * (1 + step + wave)
        points.append({"date": f"-{rows_n - i - 1}d", "close": round(price, 2)})
    return {
        "ticker": ticker,
        "period": period,
        "source": "DEMO simulated history",
        "points": points,
        "current_price": (await get_quote(ticker))["price"],
    }


KNOWN_SYMBOLS = {
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA", "amazon": "AMZN",
    "google": "GOOGL", "alphabet": "GOOGL", "tesla": "TSLA", "meta": "META",
    "netflix": "NFLX", "intel": "INTC", "amd": "AMD", "coca cola": "KO",
    "coca-cola": "KO", "walmart": "WMT", "disney": "DIS", "sap": "SAP.DE",
    "siemens": "SIE.DE", "bmw": "BMW.DE", "volkswagen": "VOW3.DE", "allianz": "ALV.DE",
    "mcdonald": "MCD", "asml": "ASML",
}


@mcp.tool()
def search_stock(query: str) -> dict:
    """Resolve company names to stock tickers (built-in list of common US/German names)."""
    query_key = query.lower().strip()
    matches = [
        {"symbol": sym, "name": name.title()}
        for name, sym in KNOWN_SYMBOLS.items()
        if query_key in name or name in query_key
    ]
    return {"results": matches[:6]}


if __name__ == "__main__":
    mcp.run()

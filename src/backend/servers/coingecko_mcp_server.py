import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("coingecko")

BASE_URL = "https://api.coingecko.com/api/v3"


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(f"{BASE_URL}{path}", params=params)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_price(ids: str, vs_currency: str = "usd") -> dict:
    """Current price for comma-separated coin ids, e.g. 'bitcoin,ethereum'."""
    data = await _get(
        "/simple/price",
        {"ids": ids, "vs_currencies": vs_currency, "include_24hr_change": "true"},
    )
    return data


@mcp.tool()
async def get_trending() -> dict:
    """Currently trending coins on CoinGecko."""
    data = await _get("/search/trending")
    return {
        "coins": [
            {"id": c["item"]["id"], "name": c["item"]["name"], "rank": c["item"]["market_cap_rank"]}
            for c in data.get("coins", [])
        ]
    }


@mcp.tool()
async def search_coins(query: str) -> dict:
    """Search for coins by name or symbol, e.g. 'solana'."""
    data = await _get("/search", {"query": query})
    return {
        "coins": [
            {"id": c["id"], "name": c["name"], "symbol": c["symbol"]}
            for c in data.get("coins", [])[:5]
        ]
    }




FNG_URL = "https://api.alternative.me/fng/"

NEWS_FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
]


@mcp.tool()
async def get_global_market() -> dict:
    """Global crypto market overview: total market cap, BTC/ETH dominance, 24h volume."""
    data = await _get("/global")
    d = data.get("data", {})
    return {
        "total_market_cap_usd": d.get("total_market_cap", {}).get("usd"),
        "total_volume_24h_usd": d.get("total_volume", {}).get("usd"),
        "btc_dominance_pct": d.get("market_cap_percentage", {}).get("btc"),
        "eth_dominance_pct": d.get("market_cap_percentage", {}).get("eth"),
        "active_coins": d.get("active_cryptocurrencies"),
        "market_cap_change_24h_pct": d.get("market_cap_change_percentage_24h_usd"),
    }


@mcp.tool()
async def get_fear_greed() -> dict:
    """Crypto Fear & Greed Index (alternative.me, 0=extreme fear, 100=extreme greed)."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(FNG_URL, params={"limit": 8})
        response.raise_for_status()
        data = response.json()
    entries = [
        {"value": int(e["value"]), "label": e["value_classification"], "date": e["timestamp"]}
        for e in data.get("data", [])
    ]
    return {"current": entries[0], "history": entries[1:]}


@mcp.tool()
async def get_top_movers(count: int = 5) -> dict:
    """Top gainers and losers (24h) among large caps: one market-cap page, sorted locally."""
    count = max(3, min(int(count), 10))
    rows = await _get("/coins/markets", {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "price_change_percentage": "24h",
        "sparkline": "false",
    })
    def _fmt(rows):
        return [
            {
                "symbol": r["symbol"].upper(), "name": r["name"],
                "price_usd": r["current_price"],
                "change_24h_pct": r.get("price_change_percentage_24h"),
            }
            for r in rows
            if r.get("price_change_percentage_24h") is not None
        ]
    fmt = _fmt(rows)
    gainers = sorted(fmt, key=lambda r: r["change_24h_pct"], reverse=True)[:count]
    losers = sorted(fmt, key=lambda r: r["change_24h_pct"])[:count]
    return {"gainers": gainers, "losers": losers}


@mcp.tool()
async def get_news(limit: int = 8) -> dict:
    """Latest crypto headlines from CoinDesk, Cointelegraph and Decrypt (RSS)."""
    import xml.etree.ElementTree as ET
    limit = max(3, min(int(limit), 15))
    items = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for source, feed in NEWS_FEEDS:
            try:
                response = await client.get(feed)
                response.raise_for_status()
                root = ET.fromstring(response.text)
                for entry in root.iter("item"):
                    title = (entry.findtext("title") or "").strip()
                    link = (entry.findtext("link") or "").strip()
                    pub = (entry.findtext("pubDate") or "").strip()
                    if title:
                        items.append({"source": source, "title": title, "link": link, "published": pub})
            except Exception:
                continue
    seen = set()
    unique = []
    for item in items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return {"news": unique[:limit]}


if __name__ == "__main__":
    mcp.run()

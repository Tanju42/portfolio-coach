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


if __name__ == "__main__":
    mcp.run()

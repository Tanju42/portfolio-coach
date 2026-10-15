import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("demo-exchange")

SEED = Path(__file__).resolve().parent / "demo_portfolio.json"

DEMO_POSITIONS = [
    {"asset": "BTC", "qty": 0.15, "avg_cost_usd": 58000.0},
    {"asset": "ETH", "qty": 2.5, "avg_cost_usd": 2600.0},
    {"asset": "SOL", "qty": 40.0, "avg_cost_usd": 130.0},
    {"asset": "AVAX", "qty": 55.0, "avg_cost_usd": 42.0},
    {"asset": "DOGE", "qty": 12000.0, "avg_cost_usd": 0.16},
]


def _load_overrides() -> dict:
    if SEED.exists():
        return json.loads(SEED.read_text())
    return {}


@mcp.tool()
def get_demo_portfolio() -> dict:
    """Simulated demo portfolio (no real account): holdings with average cost basis.
    Prices come from the live market-data tools, so values are realistic."""
    positions = _load_overrides().get("positions", DEMO_POSITIONS)
    return {
        "account_type": "DEMO",
        "note": "Simulated demo account for trying the app without an exchange connection.",
        "balances": [
            {"asset": p["asset"], "free": p["qty"], "locked": 0.0, "avg_cost_usd": p["avg_cost_usd"]}
            for p in positions
        ],
    }


if __name__ == "__main__":
    mcp.run()

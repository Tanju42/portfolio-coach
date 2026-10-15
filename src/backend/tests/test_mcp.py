import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import Agent
from app.config import Settings
from app.llm import OpenAICompatClient
from app.mcp_manager import MCPManager, load_server_configs

SERVERS_DIR = Path(__file__).resolve().parent.parent / "servers"

needs_model = pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="local LLM endpoint not configured",
)


@pytest.mark.anyio
async def test_mcp_servers_start_and_expose_tools():
    manager = MCPManager(load_server_configs(SERVERS_DIR / "mcp_servers.json"))
    try:
        await manager.start()
        specs = await manager.list_tool_specs()
        names = {spec.name for spec in specs}
        assert "binance_get_ticker" in names
        assert "coingecko_get_price" in names
        result = await specs[0].handler({"symbol": "BTCUSDT"})
        assert result["is_error"] is False
    finally:
        await manager.stop()


@needs_model
@pytest.mark.anyio
async def test_agent_answers_price_question_via_mcp():
    settings = Settings(
        llm_base_url=os.environ["LLM_BASE_URL"],
        llm_model=os.environ["LLM_MODEL"],
        llm_api_key=os.environ["LLM_API_KEY"],
    )
    client = OpenAICompatClient(settings)
    manager = MCPManager(load_server_configs(SERVERS_DIR / "mcp_servers.json"))
    try:
        await manager.start()
        agent = Agent(client, await manager.list_tool_specs())
        result = await agent.run(
            [{"role": "user", "content": "What is the current BTC price in USDT? Use your tools."}]
        )
    finally:
        await manager.stop()

    assert "$" in result.content or "USD" in result.content.upper()
    assert result.tool_trace, "agent should have called a market-data tool"
    assert result.tool_trace[0]["name"] in {
        "binance_get_ticker",
        "coingecko_get_price",
    }

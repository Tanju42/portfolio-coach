import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import ToolSpec
from app.analytics import (
    DEFAULT_TARGETS,
    asset_category,
    expand_targets,
    exposure,
    rebalance_suggestions,
    risk_report,
)
from app.memory import MemoryStore
from app.portfolios import build_all_portfolios, history_series, merge_rows, record_snapshots


TICKERS = {"BTC": 96000.0, "ETH": 3400.0, "SOL": 190.0, "AVAX": 40.0, "DOGE": 0.18}
QUOTES = {"AAPL": 248.0, "MSFT": 508.0}


def fake_spec(name: str, payload):
    async def handler(arguments=None):
        if callable(payload):
            return {"content": [{"type": "text", "text": json.dumps(payload(arguments))}]}
        return {"content": [{"type": "text", "text": json.dumps(payload)}]}

    return ToolSpec(name=name, description=name, parameters={"type": "object"}, handler=handler)


def make_specs(broker_fails: bool = False, binance_account: dict | None = None):
    crypto = {
        "account_type": "DEMO",
        "balances": [
            {"asset": "BTC", "free": 0.15, "locked": 0.0, "avg_cost_usd": 58000.0},
            {"asset": "SOL", "free": 40.0, "locked": 0.0, "avg_cost_usd": 130.0},
        ],
    }
    broker = {
        "account_type": "DEMO",
        "balances": [
            {"asset": "AAPL", "free": 12, "locked": 0.0, "avg_cost_usd": 148.0},
            {"asset": "MSFT", "free": 8, "locked": 0.0, "avg_cost_usd": 310.0},
        ],
    }

    def broker_payload(arguments=None):
        if broker_fails:
            raise RuntimeError("broker down")
        return broker

    specs = [
        fake_spec("demo-exchange_get_demo_portfolio", crypto),
        fake_spec("demo-exchange_get_demo_broker_portfolio", broker_payload),
        fake_spec(
            "binance_get_ticker",
            lambda args: {"last_price": TICKERS.get(args["symbol"][:-4], 0.0), "price_change_percent_24h": 1.5}
            if args["symbol"][:-4] in TICKERS
            else {"error": "unknown symbol"},
        ),
        fake_spec(
            "stocks_get_quote",
            lambda args: {"price": QUOTES.get(args["ticker"], 0.0), "change_pct": 0.4}
            if args["ticker"] in QUOTES
            else {"error": "unknown ticker"},
        ),
    ]
    if binance_account:
        specs.append(fake_spec("binance_get_account_assets", binance_account))
    return specs


class FakeManager:
    def __init__(self, specs):
        self._specs = specs

    async def list_tool_specs(self):
        return self._specs


@pytest.mark.asyncio
async def test_build_all_returns_two_portfolios_with_totals():
    manager = FakeManager(make_specs())
    result = await build_all_portfolios(manager, {}, "demo")
    ok = [p for p in result["portfolios"] if p["status"] == "ok"]
    assert len(result["portfolios"]) == 3
    assert len(ok) == 2
    btc = next(r for r in result["rows"] if r["asset"] == "BTC")
    assert btc["value_usd"] == pytest.approx(0.15 * 96000.0, abs=0.01)
    assert btc["avg_cost_usd"] == pytest.approx(58000.0)
    expected = round(0.15 * 96000.0 + 40.0 * 190.0 + 12 * 248.0 + 8 * 508.0, 2)
    assert result["totals"]["total_value_usd"] == pytest.approx(expected, abs=0.01)
    assert result["totals"]["portfolio_count"] == 2


@pytest.mark.asyncio
async def test_error_isolation_one_failing_provider_keeps_rest():
    manager = FakeManager(make_specs(broker_fails=True))
    result = await build_all_portfolios(manager, {}, "demo")
    statuses = {p["provider"] + p["label"]: p["status"] for p in result["portfolios"]}
    assert statuses["demo-exchangeDemo Crypto Exchange"] == "ok"
    assert statuses["demo-exchangeDemo Brokerage"] == "error"
    assert "broker down" in result["portfolios"][1]["error"]
    assert result["totals"]["total_value_usd"] > 0
    assert all(r["asset"] not in ("AAPL", "MSFT") for r in result["rows"])


@pytest.mark.asyncio
async def test_merge_rows_combines_same_asset_across_providers():
    live_account = {
        "account_type": "LIVE",
        "balances": [{"asset": "BTC", "free": 0.05, "locked": 0.0, "avg_cost_usd": 70000.0}],
    }
    manager = FakeManager(make_specs(binance_account=live_account))
    result = await build_all_portfolios(manager, {}, "live")
    btc = next(r for r in result["rows"] if r["asset"] == "BTC")
    assert len(btc["providers"]) == 2
    assert btc["qty"] == pytest.approx(0.2)
    assert result["totals"]["portfolio_count"] == 3


def test_risk_report_flags_concentration_and_no_stables():
    rows = [
        {"asset": "DOGE", "value_usd": 900.0, "cost_usd": 800.0, "pnl_usd": 100.0,
         "basis_reliable_share": 1.0, "providers": [{"label": "Demo Crypto"}]},
        {"asset": "SOL", "value_usd": 100.0, "cost_usd": 90.0, "pnl_usd": 10.0,
         "basis_reliable_share": 1.0, "providers": [{"label": "Demo Crypto"}]},
    ]
    report = risk_report(rows, [])
    assert report["score"] < 60
    assert any("DOGE" in w for w in report["warnings"])
    assert any("stables" in w for w in report["warnings"])
    categories = {item["category"]: item for item in report["exposure"]}
    assert categories["meme"]["weight_pct"] == pytest.approx(90.0, abs=0.1)


def test_expand_targets_normalizes_and_expands_groups():
    rows = [
        {"asset": "BTC", "value_usd": 500.0, "providers": [{"label": "Demo Crypto"}]},
        {"asset": "ETH", "value_usd": 500.0, "providers": [{"label": "Demo Crypto"}]},
        {"asset": "USDT", "value_usd": 100.0, "providers": [{"label": "Demo Crypto"}]},
    ]
    expanded = expand_targets({"MAJOR": 120, "STABLES": 40}, rows)
    assert sum(expanded.values()) == pytest.approx(100.0)
    assert expanded["USDT"] == pytest.approx(25.0)
    assert expanded["BTC"] == pytest.approx(37.5)


def test_expand_targets_falls_back_to_defaults():
    expanded = expand_targets({}, [{"asset": "BTC", "value_usd": 1.0, "providers": []}])
    assert expanded["BTC"] == pytest.approx(35.0)


def test_rebalance_suggestions_math():
    rows = [
        {"asset": "BTC", "value_usd": 800.0, "providers": [{"label": "Demo Crypto Exchange"}]},
        {"asset": "AAPL", "value_usd": 200.0, "providers": [{"label": "Demo Brokerage"}]},
    ]
    targets = {"BTC": 50, "STOCKS": 50}
    result = rebalance_suggestions(rows, targets)
    by_asset = {item["asset"]: item for item in result["current"]}
    assert by_asset["BTC"]["weight_pct"] == 80.0
    assert by_asset["BTC"]["target_pct"] == 50.0
    assert by_asset["BTC"]["action"] == "sell"
    assert by_asset["BTC"]["amount_usd"] == pytest.approx(300.0, abs=0.5)
    assert by_asset["AAPL"]["action"] == "buy"
    assert by_asset["AAPL"]["amount_usd"] == pytest.approx(300.0, abs=0.5)
    assert all(item["action"] is None for item in result["current"] if item["asset"] == "USDT")


def test_asset_category_stable_and_stock():
    assert asset_category("USDT") == "stables"
    assert asset_category("AAPL", "stocks") == "stocks"
    assert asset_category("SOL") == "alt"
    assert asset_category("DOGE") == "meme"


def test_snapshot_recording_and_throttle(tmp_path):
    store = MemoryStore(tmp_path / "snap.db")
    result = {
        "portfolios": [
            {
                "provider": "demo-exchange", "label": "Demo Crypto Exchange", "status": "ok",
                "total_value_usd": 100.0, "total_cost_usd": 80.0, "total_pnl_usd": 20.0,
                "rows": [{"asset": "BTC", "value_usd": 100.0}],
            }
        ]
    }
    now = int(time.time())
    assert record_snapshots(store, result, now=now) == 1
    assert record_snapshots(store, result, now=now + 10) == 0
    assert record_snapshots(store, result, now=now + 301) == 1
    series = history_series(store, "all")
    assert len(series["points"]) == 2
    assert series["points"][0]["value_usd"] == 100.0


def test_history_series_empty_is_collecting(tmp_path):
    store = MemoryStore(tmp_path / "empty.db")
    series = history_series(store, "24h")
    assert series["collecting"] is True
    assert series["points"] == []


def test_watchlist_roundtrip(tmp_path):
    store = MemoryStore(tmp_path / "watch.db")
    assert store.add_watch("SOL", "crypto") is True
    assert store.add_watch("SOL", "crypto") is False
    assert store.add_watch("AAPL", "stocks") is True
    items = store.get_watchlist()
    assert {item["symbol"] for item in items} == {"SOL", "AAPL"}
    assert store.remove_watch("SOL") is True
    assert store.remove_watch("SOL") is False


def test_merge_rows_keeps_provider_breakdown():
    blocks = [
        {
            "status": "ok", "provider": "demo-exchange", "label": "Demo Crypto Exchange",
            "rows": [{"asset": "BTC", "qty": 0.15, "value_usd": 14400.0, "cost_usd": 8700.0,
                      "pnl_usd": 5700.0, "avg_cost_usd": 58000.0, "basis_reliable_share": 1.0,
                      "change_24h_pct": 1.2,
                      "providers": [{"provider": "demo-exchange", "label": "Demo Crypto Exchange",
                                     "qty": 0.15, "value_usd": 14400.0, "avg_cost_usd": 58000.0,
                                     "pnl_usd": 5700.0}]}],
        },
        {
            "status": "ok", "provider": "binance", "label": "Binance Live",
            "rows": [{"asset": "BTC", "qty": 0.05, "value_usd": 4800.0, "cost_usd": 3500.0,
                      "pnl_usd": 1300.0, "avg_cost_usd": 70000.0, "basis_reliable_share": 1.0,
                      "providers": [{"provider": "binance", "label": "Binance Live",
                                     "qty": 0.05, "value_usd": 4800.0, "avg_cost_usd": 70000.0,
                                     "pnl_usd": 1300.0}]}],
        },
    ]
    merged = merge_rows(blocks)
    assert len(merged) == 1
    assert merged[0]["qty"] == pytest.approx(0.2)
    assert merged[0]["value_usd"] == pytest.approx(19200.0)
    assert len(merged[0]["providers"]) == 2
    assert merged[0]["avg_cost_usd"] == pytest.approx(61000.0, rel=1e-3)
    assert merged[0]["change_24h_pct"] == pytest.approx(1.2)

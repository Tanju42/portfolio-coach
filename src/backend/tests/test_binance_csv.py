import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.binance_csv import import_binance_csv, parse_csv, classify_positions
from app.memory import ImportSummary, MemoryStore

SAMPLE = """User ID,Time,Account,Operation,Coin,Change,Remark
164111982,2025-01-01 10:00:00,Spot,Buy Crypto With Fiat,EUR,-200,
164111982,2025-01-01 10:00:05,Spot,Buy Crypto With Fiat,SOL,1.5,
164111982,2025-01-01 10:01:00,Spot,Binance Convert,BNB,0.5,
164111982,2025-01-01 10:01:00,Spot,Binance Convert,USDC,-100,
164111982,2025-01-02 10:00:00,Spot,Simple Earn Flexible Interest,USDC,0.5,
164111982,2025-01-02 10:00:05,Spot,Simple Earn Flexible Subscription,SOL,-1.0,
164111982,2025-01-03 10:00:00,Spot,Simple Earn Flexible Redemption,SOL,1.0,
164111982,2025-01-04 10:00:00,Spot,Withdraw,BNB,-0.1,
164111982,2025-01-05 10:00:00,Spot,Auto-Invest - Deduct Asset,EUR,-25,
164111982,2025-01-06 12:00:00,Spot,Sell,SOL,-0.5,
164111982,2025-01-06 12:00:00,Spot,Buy,USDC,75,
"""


def test_average_cost_and_earn_noop():
    import io

    rows = parse_csv(io.StringIO(SAMPLE))
    summary = ImportSummary(rows_total=len(rows))
    positions = classify_positions(rows, summary)
    summary.finalize()

    sol = positions["SOL"]
    # SOL: +1.5 für 220 USD (EUR 200 * 1.10) -> avg 146.67; earn moves sind No-Op
    assert sol.qty == pytest.approx(1.0)
    assert sol.avg_cost_usd == pytest.approx(220.0 / 1.5)

    bnb = positions["BNB"]
    # BNB: USDC (Cash) -> BNB = bekannter avg 200 USD; withdraw reduziert proportional
    assert bnb.qty == pytest.approx(0.4)
    assert bnb.basis_unknown_qty == pytest.approx(0.0)
    assert bnb.avg_cost_usd == pytest.approx(200.0)
    assert bnb.basis_usd == pytest.approx(80.0)

    # Auto-Invest deduct ohne Coin-Inflow -> ehrlich als unknown
    assert summary.cash_spent_unknown_target_usd == pytest.approx(25 * 1.10)
    assert summary.earn_moves == 2
    assert summary.income_events == 1
    assert summary.withdrawals == 1
    assert len(summary.warnings) == 1


def test_import_idempotent_and_survives_restart(tmp_path):
    csv_file = tmp_path / "tx.csv"
    csv_file.write_text(SAMPLE, encoding="utf-8")
    db_path = tmp_path / "portfolio.db"

    store = MemoryStore(db_path)
    first = import_binance_csv(csv_file, store)
    n_trades = len(store.get_trade_history(1_000_000))
    n_positions = len(store.get_positions())
    store.commit()
    store._conn.close()

    reopened = MemoryStore(db_path)
    assert len(reopened.get_positions()) == n_positions
    assert len(reopened.get_trade_history(1_000_000)) == n_trades

    again = import_binance_csv(csv_file, reopened)
    assert again.trades == first.trades
    assert len(reopened.get_trade_history(1_000_000)) == n_trades
    sol = next(p for p in reopened.get_positions() if p.coin == "SOL")
    assert sol.avg_cost_usd == pytest.approx(220.0 / 1.5)

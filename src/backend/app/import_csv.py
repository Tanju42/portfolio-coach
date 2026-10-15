from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.binance_csv import import_binance_csv
from app.memory import MemoryStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.import_csv",
        description="Import a Binance Transaction History CSV export and build cost basis.",
    )
    parser.add_argument("csv_file", help="Path to Binance-Transaction-History.csv")
    parser.add_argument(
        "--db",
        default="portfolio.db",
        help="SQLite database file (default: ./portfolio.db)",
    )
    args = parser.parse_args(argv)

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"error: file not found: {csv_path}", file=sys.stderr)
        return 1

    store = MemoryStore(args.db)
    summary = import_binance_csv(csv_path, store)
    print(summary.as_dict())
    print(f"\npositions in db: {len(store.get_positions())}")
    print(f"trades in db: {len(store.get_trade_history(1_000_000))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

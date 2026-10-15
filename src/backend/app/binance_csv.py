from __future__ import annotations

import csv
import math
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from app.memory import ImportSummary, Position, Trade

STABLES = {"USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP"}
FIAT = {"EUR", "USD", "GBP", "TRY", "BRL"}

FIAT_USD_RATE: dict[str, float] = {"EUR": 1.10, "USD": 1.0, "GBP": 1.30}

INCOME_OPS = (
    "reward", "airdrop", "interest", "distribution", "rebate", "referral",
    "cashback", "referral",
)
NOOP_OPS = {
    "Simple Earn Flexible Subscription",
    "Simple Earn Flexible Redemption",
    "Simple Earn Locked Subscription",
    "Simple Earn Locked Redemption",
}
TRANSFER_OPS = {
    "Transfer Between Spot and Funding",
    "Transfer",
    "Transfer Funds to Spot",
    "Transfer Funds to Funding Wallet",
    "ETH 2.0 Staking",
    "BNSOL Staking",
    "SOL Staking - Purchase",
    "Liquid Swap Add",
    "Index-Auto-Investment - Redeem Positions",
}
WITHDRAW_OPS = {"Withdraw", "Spending"}
DEPOSIT_OPS = {"Deposit"}


@dataclass
class Row:
    time: str
    account: str
    operation: str
    coin: str
    change: float
    remark: str


def parse_csv(file: TextIO) -> list[Row]:
    reader = csv.DictReader(file)
    rows: list[Row] = []
    for raw in reader:
        rows.append(
            Row(
                time=(raw["Time"] or "").strip(),
                account=(raw.get("Account") or "Spot").strip(),
                operation=(raw["Operation"] or "").strip(),
                coin=(raw["Coin"] or "").strip(),
                change=float(raw["Change"]),
                remark=(raw.get("Remark") or "").strip(),
            )
        )
    rows.sort(key=lambda r: r.time)
    return rows


def is_fiat(coin: str) -> bool:
    return coin in FIAT


def is_cash(coin: str) -> bool:
    return coin in STABLES or is_fiat(coin)


def usd_rate(coin: str) -> float | None:
    if coin in STABLES:
        return 1.0
    if coin in FIAT_USD_RATE:
        return FIAT_USD_RATE[coin]
    return None


def is_income_op(operation: str) -> bool:
    lowered = operation.lower()
    return any(token in lowered for token in INCOME_OPS) and operation not in TRANSFER_OPS


def classify_positions(rows: list[Row], summary: ImportSummary | None = None) -> dict[str, Position]:
    positions: dict[str, Position] = {}
    summary = summary or ImportSummary()
    for group in _group_by_time(rows):
        _process_group(group, positions, summary)
    return positions


def build_trades(rows: list[Row]) -> list[Trade]:
    trades: list[Trade] = []
    for group in _group_by_time(rows):
        trades.extend(_group_trades(group))
    return trades


def _group_by_time(rows: list[Row], max_gap_seconds: int = 30) -> Iterator[list[Row]]:
    current: list[Row] = []
    current_end: str | None = None
    for row in rows:
        if current_end is None or _gap_seconds(current_end, row.time) <= max_gap_seconds:
            current.append(row)
            current_end = row.time
        else:
            yield current
            current = [row]
            current_end = row.time
    if current:
        yield current


def _gap_seconds(first_time: str, second_time: str) -> float:
    import datetime as dt

    fmt = "%Y-%m-%d %H:%M:%S"
    a = dt.datetime.strptime(first_time, fmt)
    b = dt.datetime.strptime(second_time, fmt)
    return abs((a - b).total_seconds())


def _pos(positions: dict[str, Position], coin: str) -> Position:
    if coin not in positions:
        positions[coin] = Position(coin=coin)
    return positions[coin]


def _reduce(position: Position, amount: float) -> float:
    if amount <= 0:
        return 0.0
    amount = min(amount, position.qty)
    avg = position.avg_cost_usd
    position.qty -= amount
    if position.qty < 1e-12:
        removed = position.basis_usd
        position.qty = 0.0
        position.basis_usd = 0.0
        position.basis_unknown_qty = 0.0
        return removed
    removed = amount * avg
    position.basis_usd -= removed
    position.basis_unknown_qty = max(0.0, position.basis_unknown_qty - amount)
    return removed


def _process_group(group: list[Row], positions: dict[str, Position], summary: ImportSummary) -> None:
    noop_rows = [r for r in group if r.operation in NOOP_OPS]
    transfer_rows = [r for r in group if r.operation in TRANSFER_OPS]
    non_trade_rows = [
        r for r in group
        if _is_non_trade(r) and r.operation not in TRANSFER_OPS and r.operation not in NOOP_OPS
    ]
    trade_rows = [
        r for r in group
        if r not in transfer_rows and r not in non_trade_rows and r not in noop_rows
    ]
    if transfer_rows:
        _process_transfer_group(transfer_rows, positions, summary)
    for row in non_trade_rows:
        _process_non_trade(row, positions, summary)
    if trade_rows:
        _process_trade_group(trade_rows, positions, summary)
    summary.earn_moves += len(noop_rows)


def _process_transfer_group(
    rows: list[Row], positions: dict[str, Position], summary: ImportSummary
) -> None:
    out_rows = [r for r in rows if r.change < 0]
    in_rows = [r for r in rows if r.change > 0]
    carried = 0.0
    for row in out_rows:
        carried += _reduce(_pos(positions, row.coin), -row.change)
    total_in = sum(r.change for r in in_rows)
    for row in in_rows:
        position = _pos(positions, row.coin)
        avg = position.avg_cost_usd
        position.qty += row.change
        if carried > 0:
            share = row.change / total_in if total_in > 0 else 0.0
            position.basis_usd += carried * share
            position.basis_unknown_qty = max(0.0, position.basis_unknown_qty)
        else:
            position.basis_usd += row.change * avg
    summary.transfers += 1


def _is_non_trade(row: Row) -> bool:
    if row.operation in TRANSFER_OPS:
        return True
    if is_income_op(row.operation):
        return True
    if row.operation in WITHDRAW_OPS:
        return True
    if row.operation in DEPOSIT_OPS and is_cash(row.coin):
        return True
    return False


def _process_non_trade(row: Row, positions: dict[str, Position], summary: ImportSummary) -> None:
    if is_income_op(row.operation):
        position = _pos(positions, row.coin)
        position.qty += row.change
        summary.income_events += 1
        return
    if row.operation in WITHDRAW_OPS:
        position = _pos(positions, row.coin)
        _reduce(position, -row.change)
        summary.withdrawals += 1
        return


def _process_trade_group(
    group: list[Row], positions: dict[str, Position], summary: ImportSummary
) -> None:
    crypto_in = [r for r in group if r.change > 0 and not is_cash(r.coin)]
    cash_in = [r for r in group if r.change > 0 and is_cash(r.coin)]
    cash_out = [r for r in group if r.change < 0 and is_cash(r.coin)]
    crypto_out = [r for r in group if r.change < 0 and not is_cash(r.coin)]
    fee_rows = [r for r in group if r.operation == "Fee"]

    if not crypto_in and not crypto_out and not cash_out:
        return
    paid_usd = 0.0
    for row in cash_out:
        rate = usd_rate(row.coin)
        if rate is None:
            summary.warnings.append(f"unknown fiat rate for {row.coin}, cash out ignored")
        else:
            paid_usd += -row.change * rate

    if crypto_in:
        total_in = sum(r.change for r in crypto_in)
        for row in crypto_out:
            _reduce(_pos(positions, row.coin), -row.change)
        for row in crypto_in:
            position = _pos(positions, row.coin)
            share = row.change / total_in if total_in > 0 else 0.0
            avg = position.avg_cost_usd
            position.qty += row.change
            if paid_usd > 0:
                position.basis_usd += paid_usd * share
            else:
                position.basis_unknown_qty += row.change
        summary.trades += 1
    elif crypto_out:
        for row in crypto_out:
            _reduce(_pos(positions, row.coin), -row.change)
        summary.trades += 1
    elif cash_out:
        for row in cash_out:
            rate = usd_rate(row.coin)
            if rate is not None:
                summary.unpaired_cash_outs.append(
                    (group[0].time, -row.change * rate)
                )
    for row in fee_rows:
        _reduce(_pos(positions, row.coin), -row.change)


def _group_trades(group: list[Row]) -> list[Trade]:
    ins = [r for r in group if r.change > 0 and not is_cash(r.coin) and r.operation != "Deposit"]
    outs = [r for r in group if r.change < 0 and not r.coin in STABLES]
    if not ins:
        return []
    trade = Trade(
        time=group[0].time,
        account=group[0].account,
        kind=group[0].operation,
        out_coin=", ".join(r.coin for r in outs) if outs else "-",
        out_amount=abs(sum(r.change for r in outs)),
        in_coin=ins[0].coin,
        in_amount=sum(r.change for r in ins),
        cost_usd=None,
        price_basis_known=False,
    )
    return [trade]


def import_binance_csv(
    csv_path: str | Path, store, source_name: str | None = None
) -> ImportSummary:
    with open(csv_path, encoding="utf-8-sig", newline="") as handle:
        rows = parse_csv(handle)
    summary = ImportSummary(rows_total=len(rows))
    positions = classify_positions(rows, summary)
    summary.finalize()
    trades = build_trades(rows)
    for trade in trades:
        store.save_trade(trade)
    for position in positions.values():
        store.upsert_position(position)
    store.save_import_summary(source_name or Path(csv_path).name, summary)
    store.commit()
    return summary


def format_position_estimate(live_qty: float, position: Position) -> dict[str, Any]:
    if position.qty > 0:
        avg = position.avg_cost_usd
        estimated_cost = avg * live_qty
        known_share = 1 - (position.basis_unknown_qty / position.qty)
    else:
        avg = 0.0
        estimated_cost = 0.0
        known_share = 0.0
    return {
        "coin": position.coin,
        "csv_qty": round(position.qty, 8),
        "avg_cost_usd": round(avg, 6),
        "estimated_cost_current_qty_usd": round(estimated_cost, 2),
        "basis_reliable_share": round(known_share, 2),
    }

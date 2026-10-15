from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Position:
    coin: str
    qty: float = 0.0
    basis_usd: float = 0.0
    basis_unknown_qty: float = 0.0

    @property
    def avg_cost_usd(self) -> float:
        return self.basis_usd / self.qty if self.qty > 0 else 0.0


@dataclass
class Trade:
    time: str
    account: str
    kind: str
    out_coin: str
    out_amount: float
    in_coin: str
    in_amount: float
    cost_usd: float | None
    price_basis_known: bool

    @property
    def unique_key(self) -> str:
        raw = f"{self.time}|{self.out_coin}|{self.out_amount}|{self.in_coin}|{self.in_amount}|{self.kind}"
        return hashlib.sha1(raw.encode()).hexdigest()


@dataclass
class ImportSummary:
    rows_total: int = 0
    trades: int = 0
    income_events: int = 0
    transfers: int = 0
    earn_moves: int = 0
    withdrawals: int = 0
    unpaired_cash_outs: list[tuple[str, float]] = field(default_factory=list)
    cash_spent_unknown_target_usd: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def finalize(self) -> None:
        self.cash_spent_unknown_target_usd = sum(
            amount for _, amount in self.unpaired_cash_outs
        )
        if self.unpaired_cash_outs:
            total = self.cash_spent_unknown_target_usd
            self.warnings.append(
                f"{len(self.unpaired_cash_outs)} cash outflow(s) (${total:.2f}) had no matching "
                "asset inflow in this export (typical for Auto-Invest plans) — "
                "cost basis for those acquisitions is unknown"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "rows_total": self.rows_total,
            "trades": self.trades,
            "income_events": self.income_events,
            "transfers": self.transfers,
            "earn_moves": self.earn_moves,
            "withdrawals": self.withdrawals,
            "cash_spent_unknown_target_usd": round(self.cash_spent_unknown_target_usd, 2),
            "warnings": self.warnings,
        }


class MemoryStore:
    """SQLite bleibt lokal (kein NFS-Mount: SQLite schlägt dort still fehl)."""

    def __init__(self, path: str | Path) -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS positions (
                coin TEXT PRIMARY KEY,
                qty REAL NOT NULL DEFAULT 0,
                basis_usd REAL NOT NULL DEFAULT 0,
                basis_unknown_qty REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS trades (
                unique_key TEXT PRIMARY KEY,
                time TEXT NOT NULL,
                account TEXT NOT NULL,
                kind TEXT NOT NULL,
                out_coin TEXT NOT NULL,
                out_amount REAL NOT NULL,
                in_coin TEXT NOT NULL,
                in_amount REAL NOT NULL,
                cost_usd REAL,
                price_basis_known INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS import_meta (
                source_file TEXT PRIMARY KEY,
                rows_total INTEGER,
                imported_at TEXT DEFAULT (datetime('now')),
                summary_json TEXT
            );
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT (datetime('now')),
                action TEXT NOT NULL,
                symbol TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                headline TEXT NOT NULL,
                rationale_json TEXT NOT NULL,
                beginner_explanation TEXT NOT NULL,
                disclaimer TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS risk_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS tracked_topics (
                topic TEXT PRIMARY KEY,
                added_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(time);
            """
        )
        self._conn.commit()

    def upsert_position(self, position: Position) -> None:
        self._conn.execute(
            """
            INSERT INTO positions (coin, qty, basis_usd, basis_unknown_qty)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(coin) DO UPDATE SET
                qty=excluded.qty, basis_usd=excluded.basis_usd,
                basis_unknown_qty=excluded.basis_unknown_qty
            """,
            (position.coin, position.qty, position.basis_usd, position.basis_unknown_qty),
        )

    def save_trade(self, trade: Trade) -> bool:
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO trades
            (unique_key, time, account, kind, out_coin, out_amount, in_coin, in_amount, cost_usd, price_basis_known)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.unique_key, trade.time, trade.account, trade.kind,
                trade.out_coin, trade.out_amount, trade.in_coin, trade.in_amount,
                trade.cost_usd, int(trade.price_basis_known),
            ),
        )
        return cursor.rowcount > 0

    def save_import_summary(self, source_file: str, summary: ImportSummary) -> None:
        self._conn.execute(
            """
            INSERT INTO import_meta (source_file, rows_total, summary_json)
            VALUES (?, ?, ?)
            ON CONFLICT(source_file) DO UPDATE SET
                rows_total=excluded.rows_total, imported_at=datetime('now'),
                summary_json=excluded.summary_json
            """,
            (source_file, summary.rows_total, json.dumps(summary.as_dict())),
        )

    def get_positions(self) -> list[Position]:
        rows = self._conn.execute("SELECT * FROM positions ORDER BY basis_usd DESC").fetchall()
        return [
            Position(
                coin=row["coin"],
                qty=row["qty"],
                basis_usd=row["basis_usd"],
                basis_unknown_qty=row["basis_unknown_qty"],
            )
            for row in rows
        ]

    def get_trade_history(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM trades ORDER BY time DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def save_signal(self, signal) -> None:
        self._conn.execute(
            """
            INSERT INTO signals
            (action, symbol, confidence, risk_level, headline, rationale_json,
             beginner_explanation, disclaimer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.action, signal.symbol, signal.confidence, signal.risk_level,
                signal.headline, json.dumps(signal.rationale),
                signal.beginner_explanation, signal.disclaimer,
            ),
        )

    def get_signals(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_risk_profile(self) -> dict[str, str]:
        rows = self._conn.execute("SELECT key, value FROM risk_profile").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.commit()

    def set_risk_profile(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO risk_profile (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            (key, value),
        )

    def add_chat_message(self, session_id: str, role: str, content: str) -> None:
        self._conn.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )

    def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def commit(self) -> None:
        self._conn.commit()

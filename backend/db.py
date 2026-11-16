"""SQLite persistence for the Chronicler agent and journal.

All writes are parameterised; no SQL is ever constructed from agent output.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from .models import JournalEntry, Position, Signal

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def get_conn(path: str | None = None) -> sqlite3.Connection:
    """Return the shared connection, creating the schema on first use."""
    global _conn
    if _conn is None:
        p = Path(path or "data/quantpilot.db")
        p.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(p), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init(_conn)
    return _conn


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS signals (
            signal_id TEXT PRIMARY KEY,
            instrument TEXT,
            bias TEXT,
            direction TEXT,
            entry_price REAL,
            stop_loss REAL,
            take_profit_1 REAL,
            take_profit_2 REAL,
            risk_reward_ratio REAL,
            confidence INTEGER,
            lot_size REAL,
            risk_amount REAL,
            created_at REAL,
            source TEXT,
            trace TEXT,
            status TEXT
        );
        CREATE TABLE IF NOT EXISTS positions (
            ticket INTEGER PRIMARY KEY,
            instrument TEXT,
            direction TEXT,
            volume REAL,
            open_price REAL,
            current_price REAL,
            sl REAL,
            tp REAL,
            open_time REAL,
            unrealized_pnl REAL,
            mode TEXT,
            magic INTEGER
        );
        CREATE TABLE IF NOT EXISTS journal (
            entry_id TEXT PRIMARY KEY,
            timestamp REAL,
            event TEXT,
            instrument TEXT,
            agent TEXT,
            summary TEXT,
            detail TEXT
        );
        CREATE TABLE IF NOT EXISTS account_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            balance REAL,
            equity REAL,
            day_pnl REAL,
            drawdown_pct REAL,
            open_risk REAL,
            mode TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_journal_ts ON journal(timestamp);
        CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(created_at);
        """
    )
    conn.commit()


def insert_signal(sig: Signal) -> None:
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sig.signal_id,
                sig.instrument,
                sig.bias,
                sig.direction,
                sig.entry_price,
                sig.stop_loss,
                sig.take_profit_1,
                sig.take_profit_2,
                sig.risk_reward_ratio,
                sig.confidence,
                sig.lot_size,
                sig.risk_amount,
                sig.created_at,
                sig.source,
                json.dumps(sig.trace),
                sig.status,
            ),
        )
        conn.commit()


def insert_position(pos: Position) -> None:
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO positions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pos.ticket,
                pos.instrument,
                pos.direction,
                pos.volume,
                pos.open_price,
                pos.current_price,
                pos.sl,
                pos.tp,
                pos.open_time,
                pos.unrealized_pnl,
                pos.mode,
                pos.magic,
            ),
        )
        conn.commit()


def delete_position(ticket: int) -> None:
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM positions WHERE ticket = ?", (ticket,))
        conn.commit()


def insert_journal(entry: JournalEntry) -> None:
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO journal VALUES (?,?,?,?,?,?,?,?,?)",
            (
                entry.entry_id,
                entry.timestamp,
                entry.event,
                entry.instrument,
                entry.agent,
                entry.summary,
                json.dumps(entry.detail),
            ),
        )
        conn.commit()


def insert_account_snapshot(balance, equity, day_pnl, drawdown_pct, open_risk, mode) -> None:
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO account_snapshots (timestamp, balance, equity, day_pnl, drawdown_pct, open_risk, mode) "
            "VALUES (?,?,?,?,?,?,?)",
            (import_time(), balance, equity, day_pnl, drawdown_pct, open_risk, mode),
        )
        conn.commit()


def fetch_signals(limit: int = 200) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def fetch_positions() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM positions ORDER BY open_time DESC").fetchall()
    return [dict(r) for r in rows]


def fetch_journal(limit: int = 200) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM journal ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def fetch_account_snapshots(limit: int = 500) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM account_snapshots ORDER BY timestamp ASC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def import_time() -> float:
    return time.time()
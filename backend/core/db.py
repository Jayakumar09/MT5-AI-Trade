"""SQLite storage layer for QUANT PILOT backend."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


class MigrationError(Exception):
    pass


def run_migrations(conn: sqlite3.Connection, migrations: list[str]) -> None:
    """Run a list of migration SQL strings idempotently."""
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL
            );
            """
        )
        applied_rows = conn.execute(
            "SELECT name FROM schema_migrations"
        ).fetchall()
        applied = {row["name"] for row in applied_rows}

        for idx, sql in enumerate(migrations):
            name = f"migration_{idx}"
            if name in applied:
                continue
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)",
                (name, datetime.now(timezone.utc).isoformat()),
            )
        conn.commit()
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        conn.rollback()
        raise MigrationError(str(exc)) from exc


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def last_insert_rowid(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT last_insert_rowid() AS id").fetchone()[0]


__all__ = ["connect", "MigrationError", "run_migrations", "now_iso", "last_insert_rowid"]
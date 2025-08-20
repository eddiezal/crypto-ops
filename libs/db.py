from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

# Repo root: .../crypto-ops
BASE_DIR: Path = Path(__file__).resolve().parents[1]

# Default DB path: <repo>/data/ledger.db  (override with env CRYPTOOPS_DB)
DEFAULT_DB_PATH: Path = BASE_DIR / "data" / "ledger.db"


def get_conn(db_path: Optional[str | os.PathLike] = None) -> sqlite3.Connection:
    """
    Return a sqlite3 connection. Ensures parent folder exists.
    Use env CRYPTOOPS_DB or DEFAULT_DB_PATH if not provided.
    """
    path = Path(db_path or os.environ.get("CRYPTOOPS_DB", DEFAULT_DB_PATH))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path.as_posix())
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def apply_schema(conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Create minimal tables used by planner/debug endpoints.
    If conn is None, this function will open a connection and close it on exit.
    """
    owns_conn = False
    if conn is None:
        conn = get_conn()
        owns_conn = True

    try:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS price (
                ts            INTEGER NOT NULL,
                instrument_id TEXT,
                symbol        TEXT NOT NULL,
                px            REAL NOT NULL,
                source        TEXT,
                PRIMARY KEY (symbol, ts)
            );

            CREATE INDEX IF NOT EXISTS idx_price_symbol_ts ON price(symbol, ts);

            CREATE TABLE IF NOT EXISTS trades (
                trade_id     TEXT PRIMARY KEY,
                strategy_id  TEXT,
                symbol       TEXT NOT NULL,
                side         TEXT,
                qty          REAL,
                entry_ts     TEXT,
                exit_ts      TEXT,
                entry_px     REAL,
                exit_px      REAL,
                fees         REAL DEFAULT 0,
                pnl_usd      REAL DEFAULT 0,
                reason       TEXT
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id        TEXT PRIMARY KEY,
                strategy_id     TEXT,
                symbol          TEXT NOT NULL,
                intent_ts       TEXT,
                ack_ts          TEXT,
                fill_ts         TEXT,
                type            TEXT,
                limit_px        REAL,
                avg_fill_px     REAL,
                qty             REAL,
                status          TEXT,
                reject_reason   TEXT,
                expected_slip_bp REAL,
                realized_slip_bp REAL
            );

            CREATE TABLE IF NOT EXISTS equity (
                ts            TEXT PRIMARY KEY,
                equity_usd    REAL NOT NULL,
                base_ccy      TEXT,
                daily_pnl_usd REAL
            );

            CREATE TABLE IF NOT EXISTS job_runs (
                job_name     TEXT,
                scheduled_ts TEXT,
                start_ts     TEXT,
                end_ts       TEXT,
                status       TEXT,
                http_code    INTEGER,
                duration_ms  INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_job_runs_start ON job_runs(start_ts);
            """
        )
        conn.commit()
    finally:
        if owns_conn:
            conn.close()

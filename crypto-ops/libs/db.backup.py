# libs/db.py
import os, sqlite3
from pathlib import Path

# Default to repo-root/data/ledger.db if LEDGER_DB is not set
BASE = Path(__file__).resolve().parents[1]
DEFAULT_DB = str(BASE / "data" / "ledger.db")

def _db_path() -> str:
    return os.getenv("LEDGER_DB", DEFAULT_DB)

def get_conn():
    """
    Returns a fresh sqlite3 connection to the planner DB.
    Honors LEDGER_DB if set; otherwise falls back to repo data/ledger.db.
    """
    path = _db_path()
    # open per-call to keep thread-safety with FastAPI workers
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    # Be tolerant under concurrency
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn

def info():
    """Small helper for debugging."""
    path = _db_path()
    try:
        import os
        size = os.path.getsize(path) if os.path.exists(path) else 0
    except Exception:
        size = 0
    return {"path": path, "size": size}

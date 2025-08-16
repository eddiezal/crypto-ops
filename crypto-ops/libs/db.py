import sqlite3, os, pathlib, datetime
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = os.getenv("LEDGER_DB_PATH", str(BASE_DIR / "data" / "ledger.db"))
def get_conn():
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
def apply_schema():
    ddl_path = BASE_DIR / "schema" / "schema.sql"
    with open(ddl_path, "r", encoding="utf-8") as f:
        ddl = f.read()
    conn = get_conn()
    conn.executescript(ddl)
    conn.commit()
    conn.close()

import sqlite3
from pathlib import Path
BASE = Path(__file__).resolve().parents[2]
conn = sqlite3.connect(BASE/"data/ledger.db")
for row in conn.execute(
    "SELECT datetime(ts,'unixepoch') as t, run_id, actions, buy_usd, sell_usd, band, nav, code_commit, mode, env "
    "FROM run_log ORDER BY ts DESC LIMIT 10"):
    print(row)

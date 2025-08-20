import argparse
from libs.db import get_conn
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", required=True, help="CSV like BTC-USD,ETH-USD,SOL-USD")
    p.add_argument("--kind", default="crypto")
    args = p.parse_args()
    conn = get_conn(); cur = conn.cursor()
    for sym in [s.strip() for s in args.symbols.split(",") if s.strip()]:
        cur.execute("INSERT OR IGNORE INTO instrument(id,symbol,kind) VALUES(?,?,?)",(sym, sym, args.kind))
    conn.commit(); conn.close()
    print("Inserted (or already existed):", args.symbols)

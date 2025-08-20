import argparse, datetime
from libs.db import get_conn
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--account","-a", default="trading")
    p.add_argument("--pairs", action="append", help="Repeatable: SYMBOL=qty (e.g., USD=50000, BTC-USD=1.2)")
    args = p.parse_args()
    if not args.pairs:
        raise SystemExit("Provide at least one --pairs SYMBOL=qty.")
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn(); cur = conn.cursor()
    for kv in args.pairs:
        if "=" not in kv: continue
        sym, v = kv.split("=",1); sym = sym.strip(); qty = float(v)
        kind = "fiat" if sym.upper()=="USD" else "crypto"
        cur.execute("INSERT OR IGNORE INTO instrument(id,symbol,kind) VALUES(?,?,?)",(sym, sym, kind))
        cur.execute("INSERT INTO balance_snapshot(ts,account_id,instrument_id,qty) VALUES(?,?,?,?)",(ts, args.account, sym, qty))
    conn.commit(); conn.close()
    print("Balances set at", ts)


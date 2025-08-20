import argparse, datetime
from libs.db import get_conn
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--btc", type=float)
    p.add_argument("--eth", type=float)
    p.add_argument("--pair", action="append", help="Repeatable: e.g., --pair SOL-USD=155")
    args = p.parse_args()
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn(); cur = conn.cursor()
    pairs = []
    if args.btc is not None: pairs.append(("BTC-USD", args.btc))
    if args.eth is not None: pairs.append(("ETH-USD", args.eth))
    for kv in (args.pair or []):
        if "=" not in kv: continue
        sym, v = kv.split("=",1); sym = sym.strip(); px = float(v)
        pairs.append((sym, px))
    for (sym, px) in pairs:
        # ensure instrument exists
        cur.execute("INSERT OR IGNORE INTO instrument(id,symbol,kind) VALUES(?,?,?)",(sym, sym, "crypto" if sym!="USD" else "fiat"))
        cur.execute("INSERT INTO price(ts,instrument_id,px,source) VALUES(?,?,?,?)",(ts, sym, px, "manual"))
    conn.commit(); conn.close()
    print("Prices updated at", ts, "->", ", ".join([f"{s}={p}" for s,p in pairs]))


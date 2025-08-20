import datetime
from libs.db import get_conn

def now_ts():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

if __name__ == "__main__":
    acct = "trading"
    conn = get_conn(); cur = conn.cursor()

    # t0 = latest snapshot timestamp (any instrument) for this account
    r = cur.execute("SELECT MAX(ts) AS t0 FROM balance_snapshot WHERE account_id=?", (acct,)).fetchone()
    t0 = r["t0"]
    if not t0:
        raise SystemExit("No snapshots exist; seed balances first.")

    # Baseline balances as-of t0: take the latest snapshot <= t0 per instrument
    # Get the instrument list seen in snapshots
    insts = [row["instrument_id"] for row in cur.execute("SELECT DISTINCT instrument_id FROM balance_snapshot WHERE account_id=?", (acct,))]
    bal = {}
    for inst in insts:
        r2 = cur.execute("""SELECT qty FROM balance_snapshot 
                            WHERE account_id=? AND instrument_id=? AND ts<=?
                            ORDER BY ts DESC LIMIT 1""",(acct, inst, t0)).fetchone()
        if r2: bal[inst] = r2["qty"]

    # Replay trades after t0
    trades = list(cur.execute("""SELECT ts,instrument_id,side,qty,px,fee_qty,fee_instrument_id
                                 FROM trade WHERE account_id=? AND ts>?
                                 ORDER BY ts ASC""",(acct, t0)))
    # Helper to get latest known price for fees
    def latest_price(sym):
        r = cur.execute("SELECT px FROM price WHERE instrument_id=? ORDER BY ts DESC LIMIT 1",(sym,)).fetchone()
        return r["px"] if r else 0.0

    for ts, sym, side, qty, px, fee_qty, fee_inst in trades:
        # ensure keys exist
        bal.setdefault("USD", 0.0)
        bal.setdefault(sym, 0.0)
        if side == "buy":
            bal["USD"] -= qty*px
            bal[sym]   += qty
        else:
            bal["USD"] += qty*px
            bal[sym]   -= qty
        if fee_qty and fee_qty != 0:
            if fee_inst == "USD":
                bal["USD"] -= fee_qty
            elif fee_inst == "BTC-USD":
                bal["BTC-USD"] = bal.get("BTC-USD",0.0) - fee_qty
                bal["USD"] -= fee_qty * latest_price("BTC-USD")
            elif fee_inst == "ETH-USD":
                bal["ETH-USD"] = bal.get("ETH-USD",0.0) - fee_qty
                bal["USD"] -= fee_qty * latest_price("ETH-USD")

    # Write new snapshot for all instruments seen
    ts_new = now_ts()
    for inst, q in bal.items():
        cur.execute("""
            INSERT INTO balance_snapshot(ts,account_id,instrument_id,qty)
            VALUES(?,?,?,?)
            ON CONFLICT(ts,account_id,instrument_id) DO UPDATE SET qty=excluded.qty
        """,(ts_new, acct, inst, q))
    conn.commit()
    print("Rebuilt snapshot at", ts_new)
    # Print a quick summary
    usd = bal.get("USD",0.0)
    btc = bal.get("BTC-USD",0.0); eth = bal.get("ETH-USD",0.0)
    link = bal.get("LINK-USD",0.0); sol = bal.get("SOL-USD",0.0)
    print(f"USD={usd:.2f}, BTC={btc:.6f}, ETH={eth:.6f}, LINK={link:.6f}, SOL={sol:.6f}")

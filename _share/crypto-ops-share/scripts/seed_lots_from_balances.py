import datetime
from libs.db import get_conn

def now_ts():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    conn = get_conn(); cur = conn.cursor()
    # last snapshot qty per instrument for 'trading'
    rows = cur.execute("""
        SELECT bs1.instrument_id, bs1.qty
        FROM balance_snapshot bs1
        WHERE bs1.account_id='trading'
          AND bs1.ts = (SELECT MAX(ts) FROM balance_snapshot bs2 WHERE bs2.account_id=bs1.account_id AND bs2.instrument_id=bs1.instrument_id)
    """).fetchall()
    created = []
    ts = now_ts()
    for r in rows:
        instr, qty = r["instrument_id"], r["qty"]
        if instr == "USD" or qty <= 0: 
            continue
        has_lot = cur.execute("SELECT 1 FROM lot WHERE account_id='trading' AND instrument_id=? AND remaining_qty>0 LIMIT 1",(instr,)).fetchone()
        if has_lot:
            continue
        pxr = cur.execute("SELECT px FROM price WHERE instrument_id=? ORDER BY ts DESC LIMIT 1",(instr,)).fetchone()
        if not pxr: 
            continue
        px = pxr["px"]
        lot_id = "lot_"+datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        cur.execute("INSERT INTO lot(id,open_ts,account_id,instrument_id,open_qty,open_px,remaining_qty) VALUES(?,?,?,?,?,?,?)",
                    (lot_id, ts, "trading", instr, qty, px, qty))
        created.append((instr, qty, px))
    conn.commit()
    if created:
        for instr, qty, px in created:
            print(f"Seeded lot for {instr}: qty={qty} @ ${px}")
    else:
        print("No lots needed (either none to seed or already present).")

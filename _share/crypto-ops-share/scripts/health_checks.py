import argparse, json, datetime, math, statistics
from pathlib import Path
from libs.db import get_conn

BASE = Path(__file__).resolve().parents[1]

def get_cfg():
    import json
    with open(BASE / "configs" / "policy.rebalancer.json","r",encoding="utf-8") as f:
        return json.load(f)

def latest_qty(cur, account, instr):
    r = cur.execute("SELECT qty FROM balance_snapshot WHERE account_id=? AND instrument_id=? ORDER BY ts DESC LIMIT 1",(account,instr)).fetchone()
    return r["qty"] if r else 0.0

def load_dense_daily(cur, pairs, days):
    ph = ",".join(["?"]*len(pairs))
    rows = cur.execute(f"""
        SELECT substr(ts,1,10) AS d, instrument_id, px
        FROM price
        WHERE instrument_id IN ({ph})
        ORDER BY d ASC, instrument_id ASC
    """, pairs).fetchall()
    by_day = {}
    for r in rows:
        d = r["d"]; by_day.setdefault(d,{})[r["instrument_id"]] = r["px"]
    dense = [(d, by_day[d]) for d in sorted(by_day) if all(s in by_day[d] for s in pairs)]
    return dense[-days:] if days>0 else dense

def price_age_seconds(cur, symbol):
    r = cur.execute("SELECT ts FROM price WHERE instrument_id=? ORDER BY ts DESC LIMIT 1",(symbol,)).fetchone()
    if not r: return None
    ts = r["ts"]
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except:
        try:
            dt = datetime.datetime.fromisoformat(ts)
        except:
            return None
    dt = dt.replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    return (now - dt).total_seconds()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min_age_sec", type=int, default=900)
    ap.add_argument("--max_30d_dd", type=float, default=-0.12)
    args = ap.parse_args()

    cfg = get_cfg()
    pairs = sorted([f"{k.upper()}-USD" for k in cfg.get("targets_trading",{}).keys() if k.upper()!="USD"])
    conn = get_conn(); cur = conn.cursor()

    # A) Price freshness
    stale = {}
    for s in pairs:
        age = price_age_seconds(cur, s)
        if age is None:
            stale[s] = None
        elif age > args.min_age_sec:
            stale[s] = age
    stale_ok = (len(stale)==0)

    # B) 30-day drawdown (approx, using current holdings)
    usd = latest_qty(cur, "trading", "USD")
    qty = { s: latest_qty(cur, "trading", s) for s in pairs }
    series = load_dense_daily(cur, pairs, 31)
    navs=[]
    for d,pxmap in series:
        navs.append(usd + sum(qty[s]*pxmap[s] for s in pairs))
    mdd = 0.0
    if len(navs)>=2:
        peak = navs[0]
        for v in navs:
            peak = max(peak, v)
            dd = (v/peak) - 1.0
            mdd = min(mdd, dd)
    dd_ok = (mdd >= args.max_30d_dd)

    ok = stale_ok and dd_ok
    out = {
        "ok": ok,
        "stale_symbols": stale,         # {sym: age_sec} if stale, None if no data
        "min_price_age_sec": args.min_age_sec,
        "drawdown_30d": mdd,
        "max_30d_drawdown": args.max_30d_dd,
        "checked_pairs": pairs,
        "points": len(series)
    }
    print(json.dumps(out, indent=2))

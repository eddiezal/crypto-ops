import argparse, math, sqlite3, json, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DB = BASE / "data" / "ledger.db"

def load_cfg():
    with open(BASE / "configs" / "policy.rebalancer.json","r",encoding="utf-8") as f:
        return json.load(f)

def get_latest_qty(cur, account, instr):
    r = cur.execute("SELECT qty FROM balance_snapshot WHERE account_id=? AND instrument_id=? ORDER BY ts DESC LIMIT 1",(account,instr)).fetchone()
    return r["qty"] if r else 0.0

def load_daily_prices(cur, pairs, days):
    ph = ",".join(["?"]*len(pairs))
    rows = cur.execute(f"""
        SELECT substr(ts,1,10) AS d, instrument_id, px
        FROM price
        WHERE instrument_id IN ({ph})
        ORDER BY d ASC, instrument_id ASC
    """, pairs).fetchall()
    by_day = {}
    for r in rows:
        d = r["d"]
        by_day.setdefault(d, {})
        by_day[d][r["instrument_id"]] = r["px"]
    dense = [(d, by_day[d]) for d in sorted(by_day) if all(s in by_day[d] for s in pairs)]
    return dense[-days:] if days>0 else dense

def eff_px(px, side, fee_bps, slip_bps):
    adj = (fee_bps + slip_bps)/10000.0
    return px*(1+adj) if side=="buy" else px*(1-adj)

def round_step(q, step):
    if step<=0: return q
    return math.floor(q/step)*step

def backtest(days=120, account="trading", rf_annual=0.0):
    cfg = load_cfg()
    targets = { (k.upper()+"-USD"): float(v) for k,v in cfg.get("targets_trading",{}).items() if k.upper()!="USD" }
    band   = float(cfg.get("bands_pct",0.05))
    mf     = float(cfg.get("move_fraction",0.5))
    fee_bp = float(cfg.get("taker_fee_bps",0.0))
    slp_bp = float(cfg.get("slippage_bps",0.0))
    qstep  = { (k.upper()+"-USD"): float(v) for k,v in cfg.get("qty_step",{}).items() }
    min_usd= float(cfg.get("min_trade_usd",1000))
    daily_cap = float(cfg.get("daily_turnover_cap_usd",1e15))
    per_asset_caps = { (k.upper()+"-USD"): float(v) for k,v in cfg.get("per_asset_cap_usd",{}).items() }
    mom = cfg.get("momentum", {})
    mom_en = bool(mom.get("enabled", False))
    look = int(mom.get("lookback_days",60))
    tilt_max = float(mom.get("tilt_max_pct",0.05))
    tilt_strength = float(mom.get("tilt_strength",1.0))

    pairs = sorted(targets.keys())

    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # start from current balances
    usd = get_latest_qty(cur, account, "USD")
    qty = { s: get_latest_qty(cur, account, s) for s in pairs }

    # load hist prices
    series = load_daily_prices(cur, pairs, days)
    if len(series)<2:
        print("Not enough price history."); return

    def past_price(sym, i_now, days_back):
        i_cut = max(0, i_now - days_back)
        for j in range(i_cut, -1, -1):
            px = series[j][1].get(sym)
            if px: return px
        return None

    navs=[]; dates=[]
    for i,(d,pxmap) in enumerate(series):
        # momentum tilt on this day
        ttargets = targets.copy()
        if mom_en and i>0:
            tilted={}
            for s in pairs:
                past = past_price(s, i, look)
                now  = pxmap[s]
                base = ttargets[s]
                if past and past>0:
                    ret = now/past - 1.0
                    tilt = max(-tilt_max, min(tilt_max, ret*tilt_strength))
                    tilted[s] = max(0.0, base*(1+tilt))
                else:
                    tilted[s] = base
            base_sum = sum(ttargets.values())
            t_sum = sum(tilted.values())
            if t_sum>0:
                for s in pairs:
                    ttargets[s] = tilted[s]*(base_sum/t_sum)

        # weights within crypto sleeve
        crypto_val = sum(qty[s]*pxmap[s] for s in pairs)
        w = { s: (qty[s]*pxmap[s]/crypto_val) if crypto_val>0 else 0.0 for s in pairs }

        # propose actions
        actions=[]
        for s in pairs:
            drift = w[s] - ttargets[s]
            if abs(drift) > band and crypto_val>0:
                usd_mv = - drift*crypto_val*mf
                side = "buy" if usd_mv>0 else "sell"
                pxe = eff_px(pxmap[s], side, fee_bp, slp_bp)
                qraw = abs(usd_mv)/pxe if pxe>0 else 0.0
                qrd  = round_step(qraw, qstep.get(s,0.0))
                usd_eff = qrd*pxe if side=="buy" else -qrd*pxe
                if qrd>0 and abs(usd_eff)>=min_usd:
                    actions.append({"s":s,"side":side,"qty":qrd,"usd":usd_eff,"pxe":pxe})

        # per-asset caps
        for a in actions:
            cap = per_asset_caps.get(a["s"])
            if cap and abs(a["usd"])>cap:
                sc = cap/abs(a["usd"])
                a["qty"]*=sc; a["usd"]*=sc

        # ensure cash
        buys = [a for a in actions if a["usd"]>0]; sells = [a for a in actions if a["usd"]<0]
        avail = usd + sum(-a["usd"] for a in sells)
        need  = sum(a["usd"] for a in buys)
        if need>avail and need>0:
            sc = avail/need if avail>0 else 0.0
            for a in buys:
                a["qty"]*=sc; a["usd"]*=sc

        # daily turnover cap
        tot = sum(abs(a["usd"]) for a in actions)
        if tot>daily_cap and tot>0:
            sc = daily_cap/tot
            for a in actions:
                a["qty"]*=sc; a["usd"]*=sc

        # drop small legs
        actions = [a for a in actions if abs(a["usd"])>=min_usd]

        # apply actions (EOD)
        for a in actions:
            if a["side"]=="buy":
                usd -= a["usd"]; qty[a["s"]] += a["qty"]
            else:
                usd += (-a["usd"]); qty[a["s"]] -= a["qty"]

        # compute NAV
        nav = usd + sum(qty[s]*pxmap[s] for s in pairs)
        navs.append(nav); dates.append(d)

    # daily returns
    rets = []
    for i in range(1,len(navs)):
        prev = navs[i-1]
        if prev>0: rets.append(navs[i]/prev - 1.0)

    if not rets:
        print("Not enough return observations."); return

    import statistics
    mu = statistics.mean(rets)
    sd = statistics.pstdev(rets) if len(rets)<2 else statistics.stdev(rets)
    ann_factor = math.sqrt(365.0)
    rf_daily = rf_annual/365.0
    sharpe = ((mu - rf_daily)/sd)*ann_factor if sd>0 else float("nan")

    # CAGR and vol
    n_days = len(rets)
    cagr = (navs[-1]/navs[0])**(365.0/n_days) - 1.0 if n_days>0 else 0.0
    ann_vol = sd*ann_factor

    # max drawdown
    peak = navs[0]; mdd = 0.0
    for v in navs:
        peak = max(peak, v)
        dd = (v/peak)-1.0
        mdd = min(mdd, dd)

    print("=== Backtest Rebalance (proxy) ===")
    print(f"Window        : {dates[0]} → {dates[-1]}  ({len(rets)} daily returns)")
    print(f"Start / End NAV: ${navs[0]:,.2f} → ${navs[-1]:,.2f}")
    print(f"Ann Return    : {cagr:.2%}")
    print(f"Ann Vol       : {ann_vol:.2%}")
    print(f"Sharpe (rf={rf_annual:.2%}) : {sharpe:.2f}")
    print(f"Max Drawdown  : {mdd:.2%}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("days", type=int, nargs="?", default=120)
    ap.add_argument("rf", type=float, nargs="?", default=0.0)
    args = ap.parse_args()
    backtest(days=args.days, account="trading", rf_annual=args.rf)

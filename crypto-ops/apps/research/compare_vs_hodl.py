import argparse, math, sqlite3, json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DB = BASE / "data" / "ledger.db"

def load_cfg():
    with open(BASE / "configs" / "policy.rebalancer.json","r",encoding="utf-8") as f:
        return json.load(f)

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

def metrics_from_nav(navs, rf_annual=0.0):
    if len(navs) < 3: return None
    rets=[]
    for i in range(1,len(navs)):
        prev = navs[i-1]
        if prev>0: rets.append(navs[i]/prev - 1.0)
    if len(rets) < 2: return None
    import statistics
    mu = statistics.mean(rets)
    sd = statistics.stdev(rets) if len(rets)>1 else 0.0
    ann_factor = math.sqrt(365.0)
    rf_daily  = rf_annual/365.0
    sharpe = ((mu - rf_daily)/sd)*ann_factor if sd>0 else float("nan")
    cagr = (navs[-1]/navs[0])**(365.0/(len(navs)-1)) - 1.0
    ann_vol = sd*ann_factor
    peak = navs[0]; mdd = 0.0
    for v in navs:
        peak = max(peak, v)
        dd = (v/peak) - 1.0
        if dd < mdd: mdd = dd
    return {"ann_return":cagr, "ann_vol":ann_vol, "sharpe":sharpe, "mdd":mdd}

def run_compare(days, rf, btc, eth, sol, link, usd, pairs_csv):
    cfg = load_cfg()
    # Target weights from policy
    cfg_targets = { (k.upper()+"-USD"): float(v) for k,v in cfg.get("targets_trading",{}).items() if k.upper()!="USD" }
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

    # Universe selection
    if pairs_csv:
        pairs = [p.strip().upper() for p in pairs_csv.split(",") if p.strip()]
    else:
        pairs = sorted(cfg_targets.keys())

    # Build starting holdings map
    start_qty = {"BTC-USD": btc, "ETH-USD": eth, "SOL-USD": sol, "LINK-USD": link}
    # Restrict to requested pairs; fill missing ones with 0
    start_qty = { s: (start_qty.get(s,0.0)) for s in pairs }

    # If we restricted pairs, adjust targets to only those (renormalize)
    targets = {}
    # Pull subset from cfg_targets; default equal if any missing
    subset = { s: cfg_targets.get(s, None) for s in pairs }
    if any(v is None for v in subset.values()):
        # fallback equal weights
        eq = 1.0/len(pairs)
        targets = { s: eq for s in pairs }
    else:
        tsum = sum(subset.values())
        targets = { s: subset[s]/tsum for s in pairs }

    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    series = load_daily_prices(cur, pairs, days)
    if len(series) < 2:
        print("Not enough price history; backfill more days."); return

    # helper: past price lookup
    def past_price(sym, i_now, days_back):
        i_cut = max(0, i_now - days_back)
        # seek back to i_cut (inclusive)
        for j in range(i_cut, -1, -1):
            px = series[j][1].get(sym)
            if px: return px
        return None

    # --- Strategy path (rebalancer) ---
    usd_s = float(usd)
    qty_s = { s: float(start_qty.get(s,0.0)) for s in pairs }
    navs_s = []
    for i,(d,pxmap) in enumerate(series):
        # momentum tilt today
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
            base_sum = sum(ttargets.values()); t_sum = sum(tilted.values())
            if t_sum>0:
                for s in pairs:
                    ttargets[s] = tilted[s]*(base_sum/t_sum)

        crypto_val = sum(qty_s[s]*pxmap[s] for s in pairs)
        w = { s: (qty_s[s]*pxmap[s]/crypto_val) if crypto_val>0 else 0.0 for s in pairs }

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

        # ensure cash via sells
        buys  = [a for a in actions if a["usd"]>0]
        sells = [a for a in actions if a["usd"]<0]
        available = usd_s + sum(-a["usd"] for a in sells)
        required  = sum(a["usd"] for a in buys)
        if required>available and required>0:
            sc = available/required if available>0 else 0.0
            for a in buys:
                a["qty"]*=sc; a["usd"]*=sc

        # daily turnover cap
        tot = sum(abs(a["usd"]) for a in actions)
        if tot>float(cfg.get("daily_turnover_cap_usd",1e15)) and tot>0:
            sc = float(cfg.get("daily_turnover_cap_usd"))/tot
            for a in actions:
                a["qty"]*=sc; a["usd"]*=sc

        actions = [a for a in actions if abs(a["usd"])>=min_usd]

        for a in actions:
            if a["side"]=="buy":
                usd_s -= a["usd"]; qty_s[a["s"]] += a["qty"]
            else:
                usd_s += (-a["usd"]); qty_s[a["s"]] -= a["qty"]

        navs_s.append(usd_s + sum(qty_s[s]*pxmap[s] for s in pairs))

    # --- HODL path ---
    qty_h = { s: float(start_qty.get(s,0.0)) for s in pairs }
    usd_h = float(usd)
    navs_h = [usd_h + sum(qty_h[s]*series[i][1][s] for s in pairs) for i in range(len(series))]

    # Metrics
    m_s = metrics_from_nav(navs_s, rf_annual=rf)
    m_h = metrics_from_nav(navs_h, rf_annual=rf)

    start_nav = navs_s[0]; end_nav_s = navs_s[-1]; end_nav_h = navs_h[-1]
    print("=== Compare: Strategy vs HODL ===")
    print(f"Window         : {series[0][0]} → {series[-1][0]}  ({len(navs_s)-1} daily returns)")
    print(f"Start NAV      : ${start_nav:,.2f}")
    print(f"End NAV (Strat): ${end_nav_s:,.2f}")
    print(f"End NAV (HODL) : ${end_nav_h:,.2f}")
    if m_s and m_h:
        print(f"Ann Ret  (Strat/HODL): {m_s['ann_return']:.2%} / {m_h['ann_return']:.2%}")
        print(f"Ann Vol  (Strat/HODL): {m_s['ann_vol']:.2%} / {m_h['ann_vol']:.2%}")
        print(f"Sharpe   (Strat/HODL): {m_s['sharpe']:.2f} / {m_h['sharpe']:.2f} (rf={rf:.2%})")
        print(f"Max DD   (Strat/HODL): {m_s['mdd']:.2%} / {m_h['mdd']:.2%}")
        delta = end_nav_s - end_nav_h
        print(f"Outperformance (End NAV): ${delta:,.2f}")
    else:
        print("Not enough observations to compute Sharpe/vol/DD.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--rf", type=float, default=0.0)
    ap.add_argument("--btc", type=float, default=2.0)
    ap.add_argument("--eth", type=float, default=30.0)
    ap.add_argument("--sol", type=float, default=0.0)
    ap.add_argument("--link", type=float, default=0.0)
    ap.add_argument("--usd", type=float, default=0.0)
    ap.add_argument("--pairs", type=str, default="")  # e.g. "BTC-USD,ETH-USD"
    args = ap.parse_args()
    run_compare(args.days, args.rf, args.btc, args.eth, args.sol, args.link, args.usd, args.pairs)

import argparse, json, sqlite3, statistics, math, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DB = BASE / "data" / "ledger.db"
CFG_PATH = BASE / "configs" / "policy.rebalancer.json"

DEFAULT_PROFILES = {
    "Defensive": {
        "risk_window_days": 90,
        "momentum_lookback_days": 60,
        "threshold_ret": 0.02,
        "tilt_strength": 0.8,
        "tilt_max_pct": 0.05,
        "satellites": ["SOL","LINK"],
        "satellite_total_cap": 0.20,
        "core_floor": 0.70,
        "smoothing_alpha": 0.25,
        "cash_auto_deploy_usd_per_day": 4000,
        "cash_floor_usd": 50000,
        "band_base": 0.04,
        "band_min": 0.025,
        "band_max": 0.07,
        "target_ann_vol": 0.30
    },
    "Balanced": {
        "risk_window_days": 90,
        "momentum_lookback_days": 60,
        "threshold_ret": 0.02,
        "tilt_strength": 1.0,
        "tilt_max_pct": 0.08,
        "satellites": ["SOL","LINK"],
        "satellite_total_cap": 0.30,
        "core_floor": 0.60,
        "smoothing_alpha": 0.30,
        "cash_auto_deploy_usd_per_day": 8000,
        "cash_floor_usd": 40000,
        "band_base": 0.035,
        "band_min": 0.02,
        "band_max": 0.08,
        "target_ann_vol": 0.35
    },
    "Aggressive": {
        "risk_window_days": 60,
        "momentum_lookback_days": 60,
        "threshold_ret": 0.00,
        "tilt_strength": 1.3,
        "tilt_max_pct": 0.10,
        "satellites": ["SOL","LINK"],
        "satellite_total_cap": 0.40,
        "core_floor": 0.50,
        "smoothing_alpha": 0.35,
        "cash_auto_deploy_usd_per_day": 15000,
        "cash_floor_usd": 30000,
        "band_base": 0.03,
        "band_min": 0.02,
        "band_max": 0.07,
        "target_ann_vol": 0.40
    }
}

CORE = {"BTC","ETH"}

def clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x

def load_cfg():
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cfg(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def daily_series(cur, sym, days):
    rows = cur.execute("SELECT ts, px FROM price WHERE instrument_id=? ORDER BY ts ASC",(sym,)).fetchall()
    by_day = {}
    for ts, px in rows:
        d = ts[:10]
        by_day[d] = px  # keep last-of-day
    dates = sorted(by_day.keys())
    if days > 0 and len(dates) > days+1:
        dates = dates[-(days+1):]
    series = [by_day[d] for d in dates]
    return dates, series

def daily_rets(series):
    r=[]
    for i in range(1,len(series)):
        prev = series[i-1]
        if prev and prev>0:
            r.append(series[i]/prev - 1.0)
    return r

def realized_vol(series):
    r = daily_rets(series)
    if len(r) < 2: return None
    return statistics.stdev(r)

def mom_ret(series, look):
    if len(series) < look+1: return None
    past = series[-(look+1)]
    now  = series[-1]
    if past and past>0:
        return now/past - 1.0
    return None

def retarget(profile_name, alpha=None, days=None, write_knobs=False, universe=None, dry_run=False):
    cfg = load_cfg()
    prof = DEFAULT_PROFILES[profile_name]

    # Universe: from provided list or from existing targets
    cur_targets = cfg.get("targets_trading", {"BTC":0.4,"ETH":0.3,"SOL":0.15,"LINK":0.15})
    assets = [a.upper() for a in (universe if universe else cur_targets.keys())]
    # ensure only the coins we actually handle
    assets = [a for a in assets if a in {"BTC","ETH","SOL","LINK"}]
    symbols = [a+"-USD" for a in assets]

    # Parameters
    risk_win = int(days if days is not None else prof["risk_window_days"])
    look_m   = int(prof["momentum_lookback_days"])
    thr      = float(prof["threshold_ret"])
    t_str    = float(prof["tilt_strength"])
    t_max    = float(prof["tilt_max_pct"])
    sats     = set(prof["satellites"])
    sat_total_cap = float(prof["satellite_total_cap"])
    core_floor = float(prof["core_floor"])
    alpha    = float(alpha if alpha is not None else prof["smoothing_alpha"])

    # Optional per-asset % cap from config.satellite_gate.max_weight_pct (if present)
    sat_cap_map = {}
    sg = cfg.get("satellite_gate", {})
    if isinstance(sg, dict) and isinstance(sg.get("max_weight_pct"), dict):
        for k,v in sg["max_weight_pct"].items():
            sat_cap_map[k.upper()] = float(v)

    # Pull series from DB
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    series = {}
    for s in symbols:
        _, ser = daily_series(cur, s, risk_win)
        series[s] = ser

    # Compute inv-vol weights (1/vol)
    inv = {}
    for s in symbols:
        vol = realized_vol(series[s])
        inv[s] = (1.0/vol) if (vol is not None and vol>0) else 0.0

    # Ensure core never zeroed out
    for core in CORE:
        sym = core+"-USD"
        if sym in inv and inv[sym]==0.0:
            inv[sym] = 1e-6

    # Momentum gating for satellites
    elig = {}
    for s in symbols:
        base = s[:-4]
        m = mom_ret(series[s], look_m)
        if base in sats:
            elig[s] = (m is not None and m >= thr)
        else:
            elig[s] = True  # core always eligible

    for s in symbols:
        if not elig[s] and s[:-4] in sats:
            inv[s] = 0.0

    # Base weights from inv-vol
    inv_sum = sum(inv.values())
    if inv_sum <= 0:
        w = {s: 1.0/len(symbols) for s in symbols}
    else:
        w = {s: inv[s]/inv_sum for s in symbols}

    # Momentum tilt (applied to all assets; satellites already gated)
    for s in symbols:
        m = mom_ret(series[s], look_m)
        t = clamp((m if m is not None else 0.0), -t_max, t_max)
        k = 1.0 + t_str * t
        w[s] *= max(0.0, k)

    # Renormalize
    tot = sum(w.values())
    if tot > 0:
        for s in symbols: w[s] /= tot

    # Enforce satellite per-asset caps (if provided)
    for s in symbols:
        a = s[:-4]
        if a in sats and a in sat_cap_map:
            if w[s] > sat_cap_map[a]:
                w[s] = sat_cap_map[a]

    # Enforce total satellite cap (scale down satellites only, give slack to core)
    sat_keys = [s for s in symbols if s[:-4] in sats]
    core_keys= [s for s in symbols if s[:-4] in CORE]
    sat_sum = sum(w[s] for s in sat_keys)
    if sat_sum > sat_total_cap and sat_sum > 0:
        scale = sat_total_cap / sat_sum
        for s in sat_keys: w[s] *= scale

    # Allocate slack to cores
    tot = sum(w.values())
    if tot < 1.0 and core_keys:
        slack = 1.0 - tot
        core_sum = sum(w[c] for c in core_keys)
        if core_sum <= 0:
            add = slack / len(core_keys)
            for c in core_keys: w[c] += add
        else:
            for c in core_keys: w[c] += slack * (w[c]/core_sum)

    # Core floor (BTC+ETH >= floor)
    core_sum = sum(w[s] for s in symbols if s[:-4] in CORE)
    if core_sum < core_floor:
        need = core_floor - core_sum
        # take proportionally from satellites
        sat_sum = sum(w[s] for s in symbols if s[:-4] in sats)
        if sat_sum > 0:
            for s in symbols:
                if s[:-4] in sats:
                    w[s] *= (1.0 - need / sat_sum)
            # renormalize to 1 by giving any rounding slack to core
            tot = sum(w.values())
            if tot < 1.0 and core_keys:
                slack = 1.0 - tot
                core_sum2 = sum(w[c] for c in core_keys)
                if core_sum2 <= 0:
                    add = slack / len(core_keys)
                    for c in core_keys: w[c] += add
                else:
                    for c in core_keys: w[c] += slack * (w[c]/core_sum2)

    # Smooth vs current targets_trading
    cur_t = {k.upper(): float(v) for k,v in cur_targets.items()}
    prop = {s[:-4]: w[s] for s in symbols}
    # fill missing keys from current targets with zero if not in universe
    for k in cur_t.keys():
        if k not in prop:
            prop[k] = 0.0

    new_t = {}
    for k in cur_t.keys():
        new_t[k] = (1.0 - alpha)*cur_t[k] + alpha*prop.get(k, 0.0)

    # Renormalize across crypto sleeve (only those in current targets universe)
    keys = list(cur_t.keys())
    total = sum(new_t[k] for k in keys)
    if total > 0:
        for k in keys: new_t[k] = new_t[k] / total

    # Write back
    out_targets = {k: round(new_t[k], 4) for k in keys}
    if not dry_run:
        cfg["targets_trading"] = out_targets
        if write_knobs:
            # apply profile knobs to policy (bands/cash/momentum gates)
            cfg.setdefault("band_dynamic", {})
            cfg["band_dynamic"]["enabled"] = True
            cfg["band_dynamic"]["base"] = prof["band_base"]
            cfg["band_dynamic"]["min"] = prof["band_min"]
            cfg["band_dynamic"]["max"] = prof["band_max"]
            cfg["band_dynamic"]["lookback_days"] = 30
            cfg["band_dynamic"]["target_ann_vol"] = prof["target_ann_vol"]

            cfg.setdefault("cash", {})
            cfg["cash"]["auto_deploy_usd_per_day"] = prof["cash_auto_deploy_usd_per_day"]
            cfg["cash"]["floor_usd"] = prof["cash_floor_usd"]
            cfg["cash"]["pro_rata_underweights"] = True

            cfg.setdefault("momentum", {})
            cfg["momentum"]["enabled"] = True
            cfg["momentum"]["lookback_days"] = prof["momentum_lookback_days"]
            cfg["momentum"]["tilt_strength"] = prof["tilt_strength"]
            cfg["momentum"]["tilt_max_pct"] = prof["tilt_max_pct"]

            cfg.setdefault("satellite_gate", {})
            cfg["satellite_gate"]["symbols"] = list(sats)
            cfg["satellite_gate"]["lookback_days"] = prof["momentum_lookback_days"]
            cfg["satellite_gate"]["threshold_ret"] = prof["threshold_ret"]
            # keep existing max_weight_pct if present

        save_cfg(cfg)

    # Print summary
    print("=== Auto-Target ===")
    print(f"Profile: {profile_name}  |  window={risk_win}d  alpha={alpha}")
    print("Current targets :", {k: round(cur_t.get(k,0.0),4) for k in sorted(cur_t)})
    print("Proposed (raw)  :", {k: round(prop.get(k,0.0),4) for k in sorted(prop)})
    print("New targets     :", {k: round(out_targets.get(k,0.0),4) for k in sorted(out_targets)})

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=list(DEFAULT_PROFILES.keys()))
    ap.add_argument("--alpha", type=float, default=None, help="smoothing toward new weights (0..1)")
    ap.add_argument("--days", type=int, default=None, help="risk window days for vol")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write-knobs", action="store_true", help="also push profile bands/cash/momentum into policy")
    ap.add_argument("--universe", action="append", help="override asset list (repeatable), e.g. --universe BTC --universe ETH ...")
    args = ap.parse_args()
    retarget(args.profile, alpha=args.alpha, days=args.days, write_knobs=args.write_knobs, universe=args.universe, dry_run=args.dry_run)

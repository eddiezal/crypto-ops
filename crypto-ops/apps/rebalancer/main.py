import os, json, argparse, math, datetime, statistics
from pathlib import Path
from libs.db import get_conn
from libs.logger import get_logger

log = get_logger("rebalancer")
BASE = Path(__file__).resolve().parents[2]
CFG_PATH = BASE / "configs" / "policy.rebalancer.json"

def load_cfg():
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def latest_price(conn, instr):
    r = conn.execute("SELECT px FROM price WHERE instrument_id=? ORDER BY ts DESC LIMIT 1",(instr,)).fetchone()
    return r["px"] if r else None

def latest_qty(conn, account, instr):
    r = conn.execute("SELECT qty FROM balance_snapshot WHERE account_id=? AND instrument_id=? ORDER BY ts DESC LIMIT 1",(account, instr)).fetchone()
    return r["qty"] if r else 0.0

def round_step(qty, step):
    if not step or step <= 0: return qty
    return math.floor(qty / step) * step  # round down so we never overspend/oversell

# ---- helpers for daily series, lookback returns, and vol ----

def _daily_series(conn, symbol, max_days):
    # Build per-day latest close from price table (robust to multiple ticks per day)
    rows = conn.execute("SELECT ts, px FROM price WHERE instrument_id=? ORDER BY ts DESC LIMIT 50000",(symbol,)).fetchall()
    by_day = {}
    for r in rows:
        d = r["ts"][:10]
        if d not in by_day:
            by_day[d] = r["px"]   # first seen is the latest that day (DESC)
        if len(by_day) >= max_days + 3:
            # enough coverage; keep scanning in case of gaps, but this is fast anyway
            pass
    days = sorted(by_day.keys())
    if len(days) < 2: return []
    # return last max_days+1 points ascending
    days = days[-(max_days+1):]
    return [(d, by_day[d]) for d in days]

def lookback_return(conn, symbol, look):
    ser = _daily_series(conn, symbol, look)
    if len(ser) < 2: return None
    start_px = ser[0][1]; end_px = ser[-1][1]
    if start_px and start_px > 0:
        return end_px / start_px - 1.0
    return None

def symbol_ann_vol(conn, symbol, look):
    ser = _daily_series(conn, symbol, look)
    if len(ser) < 3: return None
    pxs = [v for _,v in ser]
    rets = []
    for i in range(1,len(pxs)):
        if pxs[i-1] and pxs[i-1] > 0:
            rets.append(pxs[i]/pxs[i-1] - 1.0)
    if len(rets) < 2: return None
    sd = statistics.stdev(rets)
    return sd * math.sqrt(365.0)

def portfolio_ann_vol(conn, symbols, weights, look):
    # diagonal-only proxy: sqrt(sum (w_i^2 * vol_i^2))
    var = 0.0; any_vol=False
    for s in symbols:
        vol = symbol_ann_vol(conn, s, look)
        if vol is not None:
            any_vol=True
            var += (weights.get(s,0.0)**2) * (vol**2)
    return math.sqrt(var) if any_vol else None

def compute_actions(account="trading", override_prices=None):
    cfg = load_cfg()
    # base policy targets as { "BTC": 0.40, ... }
    base_targets = cfg.get("targets_trading", {})
    # working targets dict keyed by base symbols (BTC/ETH/...)
    targets = { k.upper(): float(v) for k,v in base_targets.items() if k.upper() != "USD" }

    band_cfg = cfg.get("band_dynamic", {})
    band = float(cfg.get("bands_pct", 0.05))  # legacy base band (used if dynamic disabled)
    min_usd = float(cfg.get("min_trade_usd", 1000))
    move_fraction = float(cfg.get("move_fraction", 0.5))
    daily_cap = float(cfg.get("daily_turnover_cap_usd", 1e15))
    per_asset_caps = { (k.upper()+"-USD"): float(v) for k, v in cfg.get("per_asset_cap_usd", {}).items() }
    fee_bps = float(cfg.get("taker_fee_bps", 0.0))
    slip_bps = float(cfg.get("slippage_bps", 0.0))
    qty_step = { (k.upper()+"-USD"): float(v) for k, v in cfg.get("qty_step", {}).items() }
    max_trade_count = int(cfg.get("max_trade_count", 99))
    ensure_cash = bool(cfg.get("ensure_cash", True))

    # optional features
    mom = cfg.get("momentum", {})
    mom_en = bool(mom.get("enabled", False))
    mom_look = int(mom.get("lookback_days",60))
    mom_tilt_max = float(mom.get("tilt_max_pct",0.05))
    mom_strength = float(mom.get("tilt_strength",1.0))

    gate = cfg.get("satellite_gate", {})
    gate_en = bool(gate.get("enabled", False))
    gate_syms = [s.upper() for s in gate.get("symbols", [])]
    gate_look = int(gate.get("lookback_days", 60))
    gate_thr = float(gate.get("threshold_ret", 0.0))
    gate_maxw = { k.upper(): float(v) for k,v in gate.get("max_weight_pct", {}).items() }

    cash_cfg = cfg.get("cash", {})
    cash_floor = float(cash_cfg.get("floor_usd", 0.0))
    cash_deploy = float(cash_cfg.get("auto_deploy_usd_per_day", 0.0))
    cash_prorata = bool(cash_cfg.get("pro_rata_underweights", True))

    dyn_en   = bool(band_cfg.get("enabled", False))
    dyn_base = float(band_cfg.get("base", band))
    dyn_look = int(band_cfg.get("lookback_days", 30))
    dyn_tgtv = float(band_cfg.get("target_ann_vol", 0.35))
    dyn_min  = float(band_cfg.get("min", 0.02))
    dyn_max  = float(band_cfg.get("max", 0.08))

    # instrument symbols ("BTC-USD", ...)
    symbols = sorted([f"{k.upper()}-USD" for k in targets.keys() if k.upper() != "USD"])
    conn = get_conn()

    # Gather prices/balances
    px = {}; qty = {}
    for s in symbols:
        px[s] = latest_price(conn, s)
        qty[s] = latest_qty(conn, account, s)
    usd = latest_qty(conn, account, "USD")
    # Apply overrides (what-if)
    if override_prices:
        for k, v in override_prices.items():
            k = str(k).strip()
            if k in px:
                try:
                    px[k] = float(v)
                except Exception:
                    pass
    # sanity: missing prices?
    missing = [s for s in symbols if not px[s]]
    if missing:
        return {"error": f"Missing prices for: {', '.join(missing)}"}


# === BEGIN CTO PATCH: safe override of compute_actions =========================
def _compute_actions_patched(account="trading", override_prices=None):
    import datetime, math, statistics

    cfg = load_cfg()

    # ----- Policy knobs -----
    targets = {k.upper(): float(v) for k, v in cfg.get("targets_trading", {
        "BTC": 0.40, "ETH": 0.30, "SOL": 0.15, "LINK": 0.15
    }).items() if k.upper() != "USD"}

    band = float(cfg.get("bands_pct", 0.05))
    min_usd = float(cfg.get("min_trade_usd", 1000))
    move_fraction = float(cfg.get("move_fraction", 1.0))
    daily_cap = float(cfg.get("daily_turnover_cap_usd", 1e15))
    per_asset_caps = {(k.upper() + "-USD"): float(v) for k, v in cfg.get("per_asset_cap_usd", {}).items()}
    fee_bps = float(cfg.get("taker_fee_bps", 0.0))
    slip_bps = float(cfg.get("slippage_bps", 0.0))
    qty_step = {(k.upper() + "-USD"): float(v) for k, v in cfg.get("qty_step", {}).items()}
    max_trade_count = int(cfg.get("max_trade_count", 99))
    ensure_cash = bool(cfg.get("ensure_cash", True))

    mom = cfg.get("momentum", {})
    sg  = cfg.get("satellite_gate", {})
    bd  = cfg.get("band_dynamic", {})
    cash_cfg = cfg.get("cash", {})

    symbols = sorted([f"{k}-USD" for k in targets.keys()])
    conn = get_conn()

    # ----- Latest prices / balances -----
    px, qty = {}, {}
    for s in symbols:
        p = latest_price(conn, s)
        px[s] = float(p) if p is not None else None
        q = latest_qty(conn, account, s)
        qty[s] = float(q or 0.0)
    usd = float(latest_qty(conn, account, "USD") or 0.0)

    # what-if overrides
    if override_prices:
        for k, v in override_prices.items():
            k = str(k).strip()
            if k in px:
                try: px[k] = float(v)
                except Exception: pass

    # sanity
    missing = [s for s in symbols if not px.get(s)]
    if missing:
        return {"error": f"Missing prices for: {', '.join(missing)}"}

    crypto_val = sum(qty[s] * px[s] for s in symbols)
    if crypto_val <= 0:
        return {"error": "No crypto balances; set balances first."}

    # ----- Momentum tilt (targets) -----
    if mom.get("enabled", False):
        look = int(mom.get("lookback_days", 60))
        tilt_max = float(mom.get("tilt_max_pct", 0.05))
        strength = float(mom.get("tilt_strength", 1.0))
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=look)).strftime("%Y-%m-%d 23:59:59")
        px_past = {}
        for s in symbols:
            r = conn.execute(
                "SELECT px FROM price WHERE instrument_id=? AND ts<=? ORDER BY ts DESC LIMIT 1",
                (s, cutoff)
            ).fetchone()
            px_past[s] = float(r["px"]) if r else None

        base_sum = sum(targets.values())
        t_work = {}
        for s in symbols:
            base = float(targets[s[:-4]])
            past, now = px_past.get(s), px[s]
            if past and past > 0:
                ret = now / past - 1.0
                tilt = max(-tilt_max, min(tilt_max, ret * strength))
                t_work[s] = max(0.0, base * (1.0 + tilt))
            else:
                t_work[s] = base
        t_sum = sum(t_work.values())
        if t_sum > 0:
            for s in symbols:
                targets[s[:-4]] = t_work[s] * (base_sum / t_sum)

    # ----- Satellite gate (A1) -----
    if sg.get("enabled", False):
        sat_assets = [x.upper() for x in sg.get("symbols", [])]
        sat_syms   = set(a + "-USD" for a in sat_assets)
        look = int(sg.get("lookback_days", 60))
        thr  = float(sg.get("threshold_ret", 0.0))
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=look)).strftime("%Y-%m-%d 23:59:59")

        px_past = {}
        for s in symbols:
            r = conn.execute(
                "SELECT px FROM price WHERE instrument_id=? AND ts<=? ORDER BY ts DESC LIMIT 1",
                (s, cutoff)
            ).fetchone()
            px_past[s] = float(r["px"]) if r else None

        # Zero gated satellites and reallocate proportionally to non-sat
        remove_mass = 0.0
        for s in symbols:
            if s in sat_syms:
                past, now = px_past.get(s), px[s]
                ok = (past and past > 0 and (now / past - 1.0) >= thr)
                if not ok:
                    remove_mass += targets.get(s[:-4], 0.0)
                    targets[s[:-4]] = 0.0
        if remove_mass > 0:
            core_keys = [k for k in targets.keys() if (k + "-USD") not in sat_syms]
            core_sum = sum(targets[k] for k in core_keys)
            if core_keys and core_sum > 0:
                for k in core_keys:
                    targets[k] += remove_mass * (targets[k] / core_sum)

    # ----- Weights & (simple) dynamic band (A3) -----
    weights = {s: (qty[s] * px[s] / crypto_val) for s in symbols}

    if bd.get("enabled", False):
        # approximate portfolio vol ignoring correlations
        look = int(bd.get("lookback_days", 30))
        def daily_series(sym, n):
            # pull many rows then collapse to last px per day
            rows = conn.execute(
                "SELECT ts, px FROM price WHERE instrument_id=? ORDER BY ts DESC LIMIT 2000",
                (sym,)
            ).fetchall()
            seen = set(); ser = []
            for r in rows:
                d = r["ts"][:10]
                if d in seen: continue
                seen.add(d)
                ser.append(float(r["px"]))
                if len(ser) >= n + 1: break
            return list(reversed(ser))  # chronological
        vols = {}
        for s in symbols:
            ser = daily_series(s, look)
            rets = []
            for i in range(1, len(ser)):
                prev = ser[i - 1]
                if prev > 0:
                    rets.append(ser[i] / prev - 1.0)
            if len(rets) >= 2:
                vols[s] = statistics.stdev(rets)
            else:
                vols[s] = 0.0
        port_sd_daily = math.sqrt(sum((weights[s] ** 2) * (vols.get(s, 0.0) ** 2) for s in symbols))
        ann_vol = port_sd_daily * math.sqrt(365.0)
        base = float(bd.get("base", band))
        target_ann = float(bd.get("target_ann_vol", 0.35))
        bmin = float(bd.get("min", 0.02)); bmax = float(bd.get("max", 0.08))
        band = base * (target_ann / ann_vol) if ann_vol > 0 else base
        band = max(bmin, min(bmax, band))

    # ----- Build raw actions from drift -----
    actions = []
    for s in symbols:
        tgt = float(targets[s[:-4]])
        drift = weights[s] - tgt
        if abs(drift) > band:
            usd_move = - drift * crypto_val * move_fraction   # +buy / -sell
            side = "buy" if usd_move > 0 else "sell"
            exec_adj = (fee_bps + slip_bps) / 10000.0
            px_eff = px[s] * (1 + exec_adj if side == "buy" else 1 - exec_adj)
            q_raw = abs(usd_move) / px_eff if px_eff else 0.0
            q_rd = round_step(q_raw, qty_step.get(s, 0.0))
            usd_eff = (q_rd * px_eff) if side == "buy" else - (q_rd * px_eff)
            if q_rd > 0 and abs(usd_eff) >= min_usd:
                actions.append({
                    "symbol": s, "side": side,
                    "px": px[s], "px_eff": px_eff,
                    "qty": float(q_rd), "usd": float(usd_eff),
                    "est_fee_bps": fee_bps, "est_slip_bps": slip_bps
                })

    # per-asset caps
    for a in actions:
        cap = per_asset_caps.get(a["symbol"])
        if cap is not None and abs(a["usd"]) > cap:
            sc = cap / abs(a["usd"])
            a["qty"] *= sc; a["usd"] *= sc
    actions = [a for a in actions if abs(a["usd"]) >= min_usd]

    # ensure-cash (buys <= USD + sells)
    if ensure_cash and actions:
        buys  = [a for a in actions if a["usd"] > 0]
        sells = [a for a in actions if a["usd"] < 0]
        available = usd + sum(-a["usd"] for a in sells)
        required  = sum(a["usd"] for a in buys)
        if required > available and required > 0:
            sc = (available / required) if available > 0 else 0.0
            for a in buys:
                a["qty"] *= sc; a["usd"] *= sc
            actions = [a for a in actions if abs(a["usd"]) >= min_usd]

    # cash auto-deploy cap (A2)
    cash_floor = float(cash_cfg.get("floor_usd", 0.0))
    cash_auto  = float(cash_cfg.get("auto_deploy_usd_per_day", 0.0))
    if cash_auto > 0 and actions:
        buys  = [a for a in actions if a["usd"] > 0]
        sells = [a for a in actions if a["usd"] < 0]
        net_cash_needed = sum(a["usd"] for a in buys) + sum(a["usd"] for a in sells)  # buys (+) + sells (-)
        headroom = max(0.0, usd - cash_floor)
        deploy_cap = min(cash_auto, headroom)
        if net_cash_needed > deploy_cap and net_cash_needed > 0:
            sc = (deploy_cap / net_cash_needed) if deploy_cap > 0 else 0.0
            for a in buys:
                a["qty"] = float(a["qty"] * sc)
                a["usd"] = float(a["usd"] * sc)
                a.setdefault("note", "cash_deploy")
            actions = [a for a in actions if abs(a["usd"]) >= min_usd]

    # daily turnover cap
    tot = sum(abs(a["usd"]) for a in actions)
    if tot > daily_cap and tot > 0:
        sc = daily_cap / tot
        for a in actions:
            a["qty"] = float(a["qty"] * sc)
            a["usd"] = float(a["usd"] * sc)
        actions = [a for a in actions if abs(a["usd"]) >= min_usd]

    # limit number of legs
    actions = sorted(actions, key=lambda x: abs(x["usd"]), reverse=True)[:max_trade_count]

    # final plan dict
    return {
        "account": account,
        "prices": px,
        "balances": { **{s: qty[s] for s in symbols}, "USD": usd },
        "weights": weights,
        "targets": targets,   # post-tilt, post-gate
        "crypto_val": crypto_val,
        "actions": actions,
        "config": {
            "band": band,
            "min_trade_usd": min_usd,
            "move_fraction": move_fraction,
            "daily_turnover_cap_usd": daily_cap,
            "per_asset_cap_usd": per_asset_caps,
            "taker_fee_bps": fee_bps,
            "slippage_bps": slip_bps,
            "qty_step": qty_step,
            "max_trade_count": max_trade_count,
            "ensure_cash": ensure_cash,
            "momentum": mom,
            "satellite_gate": sg,
            "band_dynamic": bd,
            "cash": cash_cfg
        }
    }

# Make it the active implementation
compute_actions = _compute_actions_patched
# === END CTO PATCH =============================================================

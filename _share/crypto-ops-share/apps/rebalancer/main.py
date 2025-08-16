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
        for k,v in override_prices.items():
            if k in px: px[k] = float(v)

    # sanity: missing prices?
    missing = [s for s in symbols if not px[s]]
    if missing:
    # === Strict cash-deploy cap (post-processing) ===
    try:
        cash_cfg = cfg.get("cash", {})
        cash_floor = float(cash_cfg.get("floor_usd", 0.0))
        cash_auto  = float(cash_cfg.get("auto_deploy_usd_per_day", 0.0))

        buys  = [a for a in actions if a["usd"] > 0]
        sells = [a for a in actions if a["usd"] < 0]
        buy_total  = sum(a["usd"]   for a in buys)
        sell_total = sum(-a["usd"]  for a in sells)

        cash_headroom = max(0.0, usd - cash_floor)
        cash_budget   = min(cash_auto, cash_headroom)

        # Net new cash required (buys beyond proceeds)
        net_cash_needed = max(0.0, buy_total - sell_total)

        if net_cash_needed > cash_budget and buy_total > 0:
            target_buys = sell_total + cash_budget
            scale = target_buys / buy_total
            for a in buys:
                a["qty"] = float(a["qty"] * scale)
                a["usd"] = float(a["usd"] * scale)
                a["note"] = "cash_deploy"
            # Drop tiny legs after scaling
            actions = [a for a in actions if abs(a["usd"]) >= min_usd]
    except Exception:
        pass

        return {"error": f"Missing prices for: {', '.join(missing)}"}

    crypto_val = sum((qty[s] or 0.0) * px[s] for s in symbols)
    if crypto_val <= 0:
    # === Strict cash-deploy cap (post-processing) ===
    try:
        cash_cfg = cfg.get("cash", {})
        cash_floor = float(cash_cfg.get("floor_usd", 0.0))
        cash_auto  = float(cash_cfg.get("auto_deploy_usd_per_day", 0.0))

        buys  = [a for a in actions if a["usd"] > 0]
        sells = [a for a in actions if a["usd"] < 0]
        buy_total  = sum(a["usd"]   for a in buys)
        sell_total = sum(-a["usd"]  for a in sells)

        cash_headroom = max(0.0, usd - cash_floor)
        cash_budget   = min(cash_auto, cash_headroom)

        # Net new cash required (buys beyond proceeds)
        net_cash_needed = max(0.0, buy_total - sell_total)

        if net_cash_needed > cash_budget and buy_total > 0:
            target_buys = sell_total + cash_budget
            scale = target_buys / buy_total
            for a in buys:
                a["qty"] = float(a["qty"] * scale)
                a["usd"] = float(a["usd"] * scale)
                a["note"] = "cash_deploy"
            # Drop tiny legs after scaling
            actions = [a for a in actions if abs(a["usd"]) >= min_usd]
    except Exception:
        pass

        return {"error": "No crypto balances; set balances first."}

    # ===== Momentum tilt on targets (if enabled) =====
    eff_targets = targets.copy()
    if mom_en:
        tilted = {}
        for s in symbols:
            base = eff_targets[s[:-4]]
            r = lookback_return(conn, s, mom_look)
            if r is not None:
                tilt = max(-mom_tilt_max, min(mom_tilt_max, r * mom_strength))
                tilted[s] = max(0.0, base * (1.0 + tilt))
            else:
                tilted[s] = base
        base_sum = sum(eff_targets.values())
        t_sum = sum(tilted.values())
        if t_sum > 0:
            for s in symbols:
                eff_targets[s[:-4]] = tilted[s] * (base_sum / t_sum)

    # ===== Satellite momentum gate (A1) =====
    if gate_en and gate_syms:
        # zero targets for gated sats with weak lookback; cap weights if max_weight_pct set
        gated = eff_targets.copy()
        for base in gate_syms:
            sym = f"{base}-USD"
            if sym in px:
                r = lookback_return(conn, sym, gate_look)
                if (r is None) or (r < gate_thr):
                    gated[base] = 0.0
                else:
                    if base in gate_maxw:
                        gated[base] = min(gated[base], gate_maxw[base])
        # renormalize to preserve total base weight
        base_sum = sum(eff_targets.values())
        g_sum = sum(gated.values())
        if g_sum > 0:
            scale = base_sum / g_sum
            for k in gated.keys():
                gated[k] = gated[k] * scale
            eff_targets = gated

    # Current weights (within crypto sleeve)
    weights = { s: (qty[s]*px[s]/crypto_val) for s in symbols }

    # ===== Dynamic bands (A3) =====
    if dyn_en:
        port_vol = portfolio_ann_vol(conn, symbols, weights, dyn_look)
        if port_vol is not None and dyn_tgtv > 0:
            dyn_band = dyn_base * (port_vol / dyn_tgtv)
            band = max(dyn_min, min(dyn_max, dyn_band))
        else:
            band = dyn_base  # fallback
    else:
        band = band  # legacy fixed band

    # ===== Drift-based actions =====
    exec_adj = (fee_bps + slip_bps) / 10000.0
    actions = []
    for s in symbols:
        tgt = float(eff_targets[s[:-4]])
        drift = weights[s] - tgt
        if abs(drift) > band:
            usd_move_drift = - drift * crypto_val * move_fraction   # + = buy, - = sell
            side = "buy" if usd_move_drift > 0 else "sell"
            px_eff = px[s] * (1 + exec_adj if side=="buy" else 1 - exec_adj)
            q_raw = abs(usd_move_drift) / px_eff if px_eff else 0.0
            q_rd  = round_step(q_raw, qty_step.get(s, 0.0))
            usd_eff = (q_rd * px_eff) if side=="buy" else - (q_rd * px_eff)
            if q_rd > 0 and abs(usd_eff) >= min_usd:
                actions.append({
                    "symbol": s, "side": side,
                    "px": px[s], "px_eff": px_eff,
                    "qty": float(q_rd), "usd": float(usd_eff),
                    "est_fee_bps": fee_bps, "est_slip_bps": slip_bps
                })

    # Per-asset caps on drift actions
    for a in actions:
        cap = per_asset_caps.get(a["symbol"])
        if cap is not None and abs(a["usd"]) > cap:
            sc = cap / abs(a["usd"])
            a["qty"] = float(a["qty"] * sc)
            a["usd"] = float(a["usd"] * sc)
    actions = [a for a in actions if abs(a["usd"]) >= min_usd]

    # Ensure cash (drift actions)
    if ensure_cash and actions:
        buys  = [a for a in actions if a["usd"] > 0]
        sells = [a for a in actions if a["usd"] < 0]
        available = usd + sum(-a["usd"] for a in sells)
        required  = sum(a["usd"] for a in buys)
        if required > available and required > 0:
            sc = available / required if available > 0 else 0.0
            for a in buys:
                a["qty"] = float(a["qty"] * sc)
                a["usd"] = float(a["usd"] * sc)
            actions = [a for a in actions if abs(a["usd"]) >= min_usd]

    # Daily turnover cap (drift actions)
    total_turnover = sum(abs(a["usd"]) for a in actions)
    if total_turnover > daily_cap and total_turnover > 0:
        sc = daily_cap / total_turnover
        for a in actions:
            a["qty"] = float(a["qty"] * sc)
            a["usd"] = float(a["usd"] * sc)
        actions = [a for a in actions if abs(a["usd"]) >= min_usd]
        total_turnover = sum(abs(a["usd"]) for a in actions)

    # ===== Cash auto-deploy (A2): buy underweights using excess cash, pro-rata =====
    if cash_deploy > 0.0:
        excess = max(0.0, usd - cash_floor)
        cap_left = max(0.0, daily_cap - total_turnover)
        budget = min(excess, cash_deploy, cap_left)
        if budget >= min_usd:
            under = { s: max(0.0, float(eff_targets[s[:-4]]) - weights[s]) for s in symbols }
            # keep only true underweights
            under = { s: u for s,u in under.items() if u > 0 }
            if under:
                if cash_prorata:
                    total_u = sum(under.values())
                    allocs = { s: budget * (u/total_u) for s,u in under.items() }
                else:
                    per = budget / len(under)
                    allocs = { s: per for s in under.keys() }

                # push pro-rata buys
                for s,usd_alloc in allocs.items():
                    if usd_alloc < min_usd: continue
                    px_eff = px[s] * (1 + exec_adj)
                    q_raw = usd_alloc / px_eff if px_eff else 0.0
                    q_rd  = round_step(q_raw, qty_step.get(s, 0.0))
                    usd_eff = q_rd * px_eff
                    if q_rd <= 0 or usd_eff < min_usd: continue

                    # per-asset cap remaining
                    cap = per_asset_caps.get(s)
                    if cap is not None:
                        used = sum(abs(a["usd"]) for a in actions if a["symbol"] == s)
                        rem = max(0.0, cap - used)
                        if rem <= 0: continue
                        if usd_eff > rem:
                            sc = rem / usd_eff
                            q_rd = float(round_step(q_rd * sc, qty_step.get(s, 0.0)))
                            usd_eff = q_rd * px_eff
                            if q_rd <= 0 or usd_eff < min_usd: continue

                    actions.append({
                        "symbol": s, "side": "buy",
                        "px": px[s], "px_eff": px_eff,
                        "qty": float(q_rd), "usd": float(usd_eff),
                        "est_fee_bps": fee_bps, "est_slip_bps": slip_bps,
                        "note": "cash_deploy"
                    })

    # limit legs
    actions = sorted(actions, key=lambda x: abs(x["usd"]), reverse=True)[:max_trade_count]
    # === Strict cash-deploy cap (post-processing) ===
    try:
        cash_cfg = cfg.get("cash", {})
        cash_floor = float(cash_cfg.get("floor_usd", 0.0))
        cash_auto  = float(cash_cfg.get("auto_deploy_usd_per_day", 0.0))

        buys  = [a for a in actions if a["usd"] > 0]
        sells = [a for a in actions if a["usd"] < 0]
        buy_total  = sum(a["usd"]   for a in buys)
        sell_total = sum(-a["usd"]  for a in sells)

        cash_headroom = max(0.0, usd - cash_floor)
        cash_budget   = min(cash_auto, cash_headroom)

        # Net new cash required (buys beyond proceeds)
        net_cash_needed = max(0.0, buy_total - sell_total)

        if net_cash_needed > cash_budget and buy_total > 0:
            target_buys = sell_total + cash_budget
            scale = target_buys / buy_total
            for a in buys:
                a["qty"] = float(a["qty"] * scale)
                a["usd"] = float(a["usd"] * scale)
                a["note"] = "cash_deploy"
            # Drop tiny legs after scaling
            actions = [a for a in actions if abs(a["usd"]) >= min_usd]
    except Exception:
        pass


    return {
        "account": account,
        "prices": px,
        "balances": { **{s: qty[s] for s in symbols}, "USD": usd },
        "weights": weights,
        "targets": { k: eff_targets[k] for k in eff_targets.keys() },
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
            "satellite_gate": gate,
            "band_dynamic": band_cfg,
            "cash": cash_cfg
        }
    }

def print_human(plan):
    if "error" in plan:
        print(plan["error"]); return
    symbols = sorted([s for s in plan["prices"].keys()])
    print("=== Rebalancer Report (multi-asset) ===")
    print("Prices:", ", ".join([f"{s}=${plan['prices'][s]:,.2f}" for s in symbols]))
    bals = ", ".join([f"{s}={plan['balances'].get(s,0.0):.6f}" for s in symbols]) + f" USD=${plan['balances'].get('USD',0.0):,.2f}"
    print("Balances:", bals)
    for s in symbols:
        tgt = plan["targets"].get(s[:-4], 0.0)
        print(f"{s}: weight {plan['weights'][s]:.2%} (tgt {tgt:.0%})")
    if plan["actions"]:
        print("-- Proposed trades (dry-run) --")
        for a in plan["actions"]:
            tag = f" [{a.get('note')}]" if a.get('note') else ""
            print(f"{a['side'].upper()} {a['qty']:.6f} {a['symbol']} (~${abs(a['usd']):,.2f}) at ${a['px_eff']:,.2f} (px eff){tag}")
    else:
        print("Within bands; No-Op.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit JSON plan to stdout")
    ap.add_argument("--pair", action="append", help="(what-if) SYMBOL=price; repeatable")
    args = ap.parse_args()
    overrides = {}
    for kv in (args.pair or []):
        if "=" in kv:
            k,v = kv.split("=",1)
            overrides[k.strip()] = float(v)
    plan = compute_actions("trading", override_prices=overrides or None)
    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print_human(plan)



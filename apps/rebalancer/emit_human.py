import argparse, math
from apps.rebalancer.main import compute_actions

def _fmt_usd(x):
    try:
        return f"${x:,.2f}"
    except Exception:
        return str(x)

def _base(sym):
    # "BTC-USD" -> "BTC"
    return sym[:-4] if sym.endswith("-USD") else sym

def print_plan(plan):
    if not isinstance(plan, dict):
        print("Planner returned unexpected object:", type(plan).__name__)
        return
    if "error" in plan:
        print("Planner error:", plan["error"])
        return

    prices   = plan.get("prices", {})
    balances = plan.get("balances", {})
    weights  = plan.get("weights", {})
    targets  = plan.get("targets", {})
    actions  = plan.get("actions", []) or []
    symbols  = sorted(prices.keys())

    print("=== Rebalancer Report (multi-asset) ===")
    # Prices
    parts = []
    for s in symbols:
        try:
            parts.append(f"{s}={_fmt_usd(float(prices[s]))}")
        except Exception:
            parts.append(f"{s}={prices[s]}")
    print("Prices:", ", ".join(parts))

    # Balances (crypto + USD)
    parts = []
    for s in symbols:
        qty = float(balances.get(s, 0.0) or 0.0)
        px  = float(prices.get(s, 0.0) or 0.0)
        val = qty * px
        parts.append(f"{s}={qty:.6f} (~{_fmt_usd(val)}) @ { _fmt_usd(px) }")
    parts.append(f"USD={_fmt_usd(float(balances.get('USD', 0.0) or 0.0))}")
    print("Balances:", "; ".join(parts))

    # Weights vs targets
    for s in symbols:
        w = float(weights.get(s, 0.0) or 0.0)
        tgt = float(targets.get(_base(s), 0.0) or 0.0)
        print(f"{s}: weight {w:.2%} (tgt {tgt:.0%})")

    # Actions
    if actions:
        print("-- Proposed trades (dry-run) --")
        for a in actions:
            side = a.get("side","").upper()
            qty  = float(a.get("qty",0) or 0)
            sym  = a.get("symbol","")
            usd  = abs(float(a.get("usd",0) or 0.0))
            px_eff = float(a.get("px_eff", a.get("px", 0.0)) or 0.0)
            note = a.get("note")
            line = f"{side} {qty:.6f} {sym} (~{_fmt_usd(usd)}) at {_fmt_usd(px_eff)}"
            if note:
                line += f" [{note}]"
            print(line)
    else:
        print("Within bands; No-Op.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", action="append", help="(what-if) SYMBOL=price; repeatable")
    args = ap.parse_args()

    overrides = {}
    for kv in (args.pair or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            overrides[k.strip()] = float(v)

    plan = compute_actions("trading", override_prices=overrides or None)
    print_plan(plan)

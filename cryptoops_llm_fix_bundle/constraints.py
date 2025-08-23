from __future__ import annotations
from typing import Dict, Any, List, Tuple

DEFAULTS = {
    "max_turnover_pct": 0.15,    # total traded notional / NAV per cycle
    "max_orders_per_cycle": 10,  # safety limit
    "max_exposure_pct": 0.85,    # any single-asset exposure cap (pre-trade)
    "min_usd_order": 25.0,       # strip dust/fees below this
}

def _nav_usd(balances: Dict[str, float], prices: Dict[str, float]) -> float:
    nav = float(balances.get("USD", 0.0))
    for sym, qty in balances.items():
        if sym == "USD":
            continue
        px = float(prices.get(f"{sym}-USD", 0.0))
        nav += float(qty) * px
    return max(nav, 1e-9)

def _action_notional_usd(a: Dict[str, Any], prices: Dict[str, float]) -> float:
    # explicit notional wins
    n = a.get("notional")
    if n is not None:
        return abs(float(n))
    # else size * px using pair or symbol
    pair = a.get("pair") or a.get("symbol")
    size = 0.0
    try:
        size = float(a.get("size", 0.0))
    except Exception:
        size = 0.0
    px = 0.0
    if pair:
        try:
            px = float(prices.get(pair, 0.0))
        except Exception:
            px = 0.0
    return abs(size * px)

def _estimate_turnover_pct_from_rebalance(actions: List[Dict[str, Any]]) -> float:
    """
    Sum absolute target-current percentage deltas (as fraction of NAV).
    e.g. BTC 0.06->65.00 (0.6494) + ETH 0.74->30.00 (0.2926) ≈ 0.942 of NAV.
    """
    tot = 0.0
    for a in actions:
        try:
            cur = float(a.get("current_pct", 0.0))
            tgt = float(a.get("target_pct", 0.0))
            tot += abs((tgt - cur) / 100.0)
        except Exception:
            pass
    return tot

def evaluate(plan: Dict[str, Any], policy: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns (possibly modified plan, hits[]). If any constraint hits:
      - actions -> []
      - config.halted = True
      - note includes "ConstraintHit: ..."
    """
    prices   = plan.get("prices", {}) or {}
    actions  = list(plan.get("actions", []) or [])
    balances = plan.get("balances", {}) or {}

    params = dict(DEFAULTS)
    params.update((policy.get("constraints") or {}))

    nav = _nav_usd(balances, prices)

    # turnover: prefer USD notional; if zero and we have % rows, estimate
    turnover = sum(_action_notional_usd(a, prices) for a in actions)
    if turnover <= 0.0 and any(("current_pct" in a and "target_pct" in a) for a in actions):
        turnover_pct = _estimate_turnover_pct_from_rebalance(actions)
    else:
        turnover_pct = (turnover / nav) if nav else 1.0

    order_count = len(actions)
    hits: List[Dict[str, Any]] = []

    if turnover_pct > float(params["max_turnover_pct"]):
        hits.append({"type": "MaxTurnover", "value": round(turnover_pct, 6), "limit": float(params["max_turnover_pct"])})

    if order_count > int(params["max_orders_per_cycle"]):
        hits.append({"type": "MaxOrders", "value": order_count, "limit": int(params["max_orders_per_cycle"])})

    max_expo = float(params["max_exposure_pct"])
    for sym, qty in balances.items():
        if sym == "USD":
            continue
        px = float(prices.get(f"{sym}-USD", 0.0))
        expo = (float(qty) * px) / nav if nav else 1.0
        if expo > max_expo:
            hits.append({"type": "MaxExposure", "asset": sym, "value": round(expo, 6), "limit": max_expo})

    # Strip dust orders below min_usd_order (not a "hit")
    min_usd = float(params["min_usd_order"])
    cleaned = [a for a in actions if _action_notional_usd(a, prices) >= min_usd]

    if hits:
        new_plan = dict(plan)
        new_plan["actions"] = []
        cfg = new_plan.setdefault("config", {})
        cfg["halted"] = True
        new_plan["note"] = "ConstraintHit: " + ", ".join(h["type"] for h in hits)
        return new_plan, hits

    if len(cleaned) != len(actions):
        plan = dict(plan)
        plan["actions"] = cleaned

    return plan, []

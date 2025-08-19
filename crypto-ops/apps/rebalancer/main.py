# apps/rebalancer/main.py
import os, json, sqlite3
from typing import Dict, List, Optional, Any
from pathlib import Path

from apps.infra.state_gcs import read_json  # balances come from GCS state

# ---------- policy/targets helpers ----------

def _load_policy_targets() -> Dict[str, float]:
    """
    Load target weights from configs/policy.rebalancer.json.
    Fallback to a sane split if the file is absent.
    """
    try:
        cfg = Path(__file__).resolve().parents[1] / "configs" / "policy.rebalancer.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        t = data.get("targets_trading") or data.get("targets") or {}
        return {k.upper(): float(v) for k, v in t.items()}
    except Exception:
        return {"BTC": 0.45, "ETH": 0.25, "SOL": 0.15, "LINK": 0.15}

def _pairs(targets: Dict[str, float]) -> List[str]:
    return [f"{k}-USD" for k in targets.keys()]

def _band_from_policy(default_band: float = 0.01) -> float:
    """
    Read band from band_dynamic {base,min,max}; clamp base into [min,max].
    """
    try:
        cfg = Path(__file__).resolve().parents[1] / "configs" / "policy.rebalancer.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        bd = data.get("band_dynamic") or {}
        base = float(bd.get("base", default_band))
        mn   = float(bd.get("min", base))
        mx   = float(bd.get("max", base))
        return max(mn, min(base, mx))
    except Exception:
        return default_band

# ---------- SQLite helpers (safe with sqlite3.Row) ----------

def _conn() -> sqlite3.Connection:
    db = os.getenv("LEDGER_DB", "/tmp/ledger.db")
    if not os.path.exists(db):
        raise RuntimeError(f"LEDGER_DB not found at {db}")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row  # dict-like rows
    return con

def _symbol_col(cur: sqlite3.Cursor) -> str:
    cols = [r[1] for r in cur.execute("PRAGMA table_info(price)").fetchall()]
    lower = [c.lower() for c in cols]
    if "symbol" in lower:        return cols[lower.index("symbol")]
    if "instrument_id" in lower: return cols[lower.index("instrument_id")]
    raise RuntimeError("price table missing symbol/instrument_id")

def _latest_prices_from_db(pairs: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    with _conn() as con:
        cur = con.cursor()
        symcol = _symbol_col(cur)
        # Using ORDER BY ts DESC LIMIT 1 for each pair
        for p in pairs:
            row = cur.execute(
                f"SELECT px FROM price WHERE {symcol}=? ORDER BY ts DESC LIMIT 1",
                (p,)
            ).fetchone()
            if row and row["px"] is not None:
                out[p] = float(row["px"])
    return out

# ---------- balances + NAV ----------

def _load_balances() -> Dict[str, float]:
    bal = read_json("state/balances.json", default=None) or {}
    if "USD" not in bal:
        bal["USD"] = 0.0
    # ensure floats
    return {k: float(v) for k, v in bal.items()}

def _nav(bal: Dict[str, float], prices: Dict[str, float]) -> float:
    nav = float(bal.get("USD", 0.0))
    for k, q in bal.items():
        if k.endswith("-USD") and k in prices:
            nav += float(q) * float(prices[k])
    return nav

# ---------- simple target-based rebalancer ----------

def _gen_actions(
    bal: Dict[str, float],
    prices: Dict[str, float],
    targets: Dict[str, float],
    band: float
) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    pairs = _pairs(targets)
    nav = _nav(bal, prices)
    if nav <= 0:
        return actions

    # desired USD exposure per pair
    target_usd = {p: nav * targets[p.split("-")[0]] for p in pairs}
    threshold = nav * float(band)

    for p in pairs:
        px = prices.get(p)
        if not px:
            continue
        cur_val = float(bal.get(p, 0.0)) * float(px)
        delta = target_usd[p] - cur_val

        # Only trade if outside band threshold
        if abs(delta) <= threshold:
            continue

        side = "buy" if delta > 0 else "sell"
        usd  = round(abs(delta), 2)
        qty  = round(usd / float(px), 8)
        actions.append({"symbol": p, "side": side, "usd": usd, "qty": qty})

    return actions

# ---------- public entry point ----------

def compute_actions(account: str, override_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    Returns:
      {
        "account": str,
        "prices": { "BTC-USD": 12345.6, ... },
        "balances": { "BTC-USD": qty, "USD": cash, ... },
        "actions": [ {symbol, side, usd, qty}, ... ],
        "config": { "band": float }
      }
    """
    targets = _load_policy_targets()
    pairs   = _pairs(targets)

    prices = (override_prices or {}).copy() if override_prices else _latest_prices_from_db(pairs)
    if not prices:
        # Let the service layer decide the fallback; signal "planner unavailable"
        raise RuntimeError("no prices available from DB; provide override_prices or load DB")

    balances = _load_balances()
    band     = _band_from_policy(0.01)  # default 1%

    actions = _gen_actions(balances, prices, targets, band)

    return {
        "account": account,
        "prices": prices,
        "balances": balances,
        "actions": actions,
        "config": {"band": band},
    }

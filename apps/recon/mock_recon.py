from decimal import Decimal
from typing import Dict, Any
import os, time, uuid, json
from apps.infra import state

# Use mock client for now
from apps.exchange.mock_client import MockCoinbaseClient

def reconcile_once(abs_usd: Decimal = Decimal("10"), pct: Decimal = Decimal("0.5")) -> Dict[str, Any]:
    """Reconcile using mock client (SAFE)"""
    
    # Get state balances
    state_bal = state.read_json("state/balances.json", default={}) or {}
    target = {
        "USD": Decimal(str(state_bal.get("USD", 0))),
        "BTC": Decimal(str(state_bal.get("BTC", 0))),
        "ETH": Decimal(str(state_bal.get("ETH", 0)))
    }
    
    # Get mock exchange balances
    client = MockCoinbaseClient()
    exch = client.get_balances()
    actual = {
        "USD": exch.get("USD", Decimal(0)),
        "BTC": exch.get("BTC", Decimal(0)),
        "ETH": exch.get("ETH", Decimal(0))
    }
    
    # Calculate drift
    drift = {}
    over = False
    
    for sym in ("USD", "BTC", "ETH"):
        d = abs(actual[sym] - target[sym])
        base = actual[sym] if actual[sym] != 0 else Decimal("1")
        pctd = (d / abs(base)) * Decimal("100")
        
        if sym == "USD":
            if d > abs_usd: over = True
        else:
            if pctd > pct: over = True
        
        drift[sym] = {
            "exchange": str(actual[sym]),
            "state": str(target[sym]),
            "drift": str(d),
            "drift_pct": str(pctd)
        }
    
    rec = {
        "ts": int(time.time()),
        "run_id": str(uuid.uuid4()),
        "mode": "MOCK",
        "ok": not over,
        "thresholds": {"abs_usd": str(abs_usd), "pct": str(pct)},
        "drift": drift
    }
    
    # Log it
    state.append_jsonl("logs/recon/mock_recon.jsonl", rec)
    
    print("✅ Mock reconciliation complete")
    return rec

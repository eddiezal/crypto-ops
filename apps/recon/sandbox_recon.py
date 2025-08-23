from decimal import Decimal
from typing import Dict, Any
import os, time, uuid, json
from apps.infra import state

# Use REAL sandbox client
from apps.exchange.sandbox_client import CoinbaseSandboxClient

def reconcile_once(abs_usd: Decimal = Decimal("100"), pct: Decimal = Decimal("5")) -> Dict[str, Any]:
    """Reconcile using REAL sandbox client"""
    
    # Get state balances
    state_bal = state.read_json("state/balances.json", default={}) or {}
    target = {
        "USD": Decimal(str(state_bal.get("USD", 0))),
        "BTC": Decimal(str(state_bal.get("BTC", 0))),
        "ETH": Decimal(str(state_bal.get("ETH", 0)))
    }
    
    # Get REAL sandbox balances
    print("\nConnecting to Coinbase sandbox...")
    client = CoinbaseSandboxClient()
    exch = client.get_balances()
    
    # Sandbox might use USDC instead of USD
    usd_balance = exch.get("USD", Decimal(0))
    if usd_balance == 0 and "USDC" in exch:
        usd_balance = exch.get("USDC", Decimal(0))
        print(f"Note: Using USDC as USD proxy: {usd_balance}")
    
    actual = {
        "USD": usd_balance,
        "BTC": exch.get("BTC", Decimal(0)),
        "ETH": exch.get("ETH", Decimal(0))
    }
    
    print(f"\nState balances: {target}")
    print(f"Sandbox balances: {actual}")
    
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
        "mode": "SANDBOX",
        "ok": not over,
        "thresholds": {"abs_usd": str(abs_usd), "pct": str(pct)},
        "drift": drift
    }
    
    # Log it
    state.append_jsonl("logs/recon/sandbox_recon.jsonl", rec)
    
    print(f"\n{'✅' if rec['ok'] else '❌'} Reconciliation: {'OK' if rec['ok'] else 'DRIFT DETECTED'}")
    return rec

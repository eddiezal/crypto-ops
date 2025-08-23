from decimal import Decimal
from typing import Dict, Any
import os, time, uuid, json

def reconcile_once(abs_usd: Decimal = Decimal("100"), pct: Decimal = Decimal("5")) -> Dict[str, Any]:
    """Fixed reconciliation - reads directly from file"""
    
    # READ DIRECTLY FROM FILE (bypass state module)
    with open('state/balances.json', 'r') as f:
        state_bal = json.load(f)
    
    target = {
        "USD": Decimal(str(state_bal.get("USD", 0))),
        "BTC": Decimal(str(state_bal.get("BTC", 0))),
        "ETH": Decimal(str(state_bal.get("ETH", 0)))
    }
    
    # Get sandbox balances
    from apps.exchange.sandbox_client import CoinbaseSandboxClient
    client = CoinbaseSandboxClient()
    exch = client.get_balances()
    
    actual = {
        "USD": exch.get("USD", Decimal(0)),
        "BTC": exch.get("BTC", Decimal(0)),
        "ETH": exch.get("ETH", Decimal(0))
    }
    
    print(f"\nDirect file read: {state_bal}")
    print(f"Target (Decimal): {target}")
    print(f"Sandbox: {actual}")
    
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
    
    # Log it (also bypass state module)
    os.makedirs('logs/recon', exist_ok=True)
    with open('logs/recon/fixed_recon.jsonl', 'a') as f:
        f.write(json.dumps(rec) + '\n')
    
    print(f"\n{'✅' if rec['ok'] else '❌'} Reconciliation: {'OK' if rec['ok'] else 'DRIFT DETECTED'}")
    return rec

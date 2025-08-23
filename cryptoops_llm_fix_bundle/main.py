"""Rebalancer with hardcoded sandbox data"""
from typing import Dict, Any, Optional

# Hardcoded sandbox data
SANDBOX_BALANCES = {
    "USD": 2683.022850014763,
    "BTC": 1.703531964692791,
    "ETH": 19.972825658393063
}

SANDBOX_PRICES = {
    "BTC-USD": 113645.055,
    "ETH-USD": 4288.045
}

def compute_actions(account: str, override_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Compute rebalancing actions with sandbox data"""
    
    prices = override_prices if override_prices else SANDBOX_PRICES
    balances = SANDBOX_BALANCES
    
    # Calculate current allocations
    btc_value = balances["BTC"] * prices.get("BTC-USD", 113645)
    eth_value = balances["ETH"] * prices.get("ETH-USD", 4288)
    usd_value = balances["USD"]
    total_value = btc_value + eth_value + usd_value
    
    # Target allocations
    targets = {
        "BTC": 0.65,  # 65%
        "ETH": 0.30,  # 30%
        "USD": 0.05   # 5%
    }
    
    # Calculate if rebalancing needed
    actions = []
    band = 0.05  # 5% band
    
    btc_current_pct = btc_value / total_value
    eth_current_pct = eth_value / total_value
    
    if abs(btc_current_pct - targets["BTC"]) > band:
        actions.append({
            "type": "rebalance",
            "asset": "BTC",
            "current_pct": round(btc_current_pct * 100, 2),
            "target_pct": targets["BTC"] * 100
        })
    
    if abs(eth_current_pct - targets["ETH"]) > band:
        actions.append({
            "type": "rebalance", 
            "asset": "ETH",
            "current_pct": round(eth_current_pct * 100, 2),
            "target_pct": targets["ETH"] * 100
        })
    
    return {
        "account": account,
        "prices": prices,
        "balances": balances,
        "actions": actions,
        "config": {"band": band},
        "total_value": round(total_value, 2),
        "allocations": {
            "BTC": round(btc_current_pct * 100, 2),
            "ETH": round(eth_current_pct * 100, 2),
            "USD": round((usd_value / total_value) * 100, 2)
        }
    }

def _band_from_policy(default_band: float = 0.01) -> float:
    """
    Resolve the rebalancing band from /configs/policy.rebalancer.{json|yaml}.
    Supports:
      - band_dynamic: { base, min, max }
      - bands_pct: <float> (legacy)
    """
    try:
        from pathlib import Path
        import json as _json

        # /workspace/apps/rebalancer/main.py  -> parents[2] == /workspace
        root = Path(__file__).resolve().parents[2]
        cfg_dir = root / "configs"
        pj = cfg_dir / "policy.rebalancer.json"
        py = cfg_dir / "policy.rebalancer.yaml"

        cfg = {}
        if pj.exists():
            cfg = _json.loads(pj.read_text(encoding="utf-8"))
        elif py.exists():
            try:
                import yaml as _yaml
                cfg = _yaml.safe_load(py.read_text(encoding="utf-8")) or {}
            except Exception:
                cfg = {}

        bd = cfg.get("band_dynamic") or {}
        if bd:
            base = float(bd.get("base", default_band))
            mn   = float(bd.get("min", base))
            mx   = float(bd.get("max", base))
            return max(mn, min(base, mx))

        if "bands_pct" in cfg:
            return float(cfg["bands_pct"])

        return default_band
    except Exception:
        return default_band

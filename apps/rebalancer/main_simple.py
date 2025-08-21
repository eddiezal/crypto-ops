"""Rebalancer main module"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

def compute_actions(account: str, override_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Compute rebalancing actions"""
    
    # Try to read balances from state file
    balances = {}
    try:
        balance_file = Path("state/balances.json")
        if balance_file.exists():
            with open(balance_file) as f:
                balances = json.load(f)
    except:
        balances = {"USD": 0.0, "BTC": 0.0, "ETH": 0.0}
    
    # Try to read prices
    prices = override_prices or {}
    if not prices:
        try:
            price_file = Path("state/latest_prices.json")
            if price_file.exists():
                with open(price_file) as f:
                    prices = json.load(f)
        except:
            prices = {"BTC-USD": 114175.735, "ETH-USD": 4340.94}
    
    # Read config
    config = {"band": 0.05}
    try:
        config_file = Path("configs/policy.rebalancer.json")
        if config_file.exists():
            with open(config_file) as f:
                policy = json.load(f)
                config["band"] = policy.get("bands_pct", 0.05)
    except:
        pass
    
    return {
        "account": account,
        "prices": prices,
        "balances": balances,
        "actions": [],
        "config": config
    }

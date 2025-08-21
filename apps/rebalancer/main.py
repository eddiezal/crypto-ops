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


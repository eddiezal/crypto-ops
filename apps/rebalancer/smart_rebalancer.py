"""Smart Portfolio Rebalancer with Order Generation"""
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Any
import json
from datetime import datetime

class PortfolioRebalancer:
    """Implements 65/30/5 BTC/ETH/USD target allocation"""
    
    def __init__(self, targets: Dict[str, float] = None):
        self.targets = targets or {
            "BTC": 0.65,  # 65%
            "ETH": 0.30,  # 30%
            "USD": 0.05   # 5%
        }
        
        self.min_order_size = {
            "BTC": Decimal("0.001"),
            "ETH": Decimal("0.01"),
            "USD": Decimal("1.0")
        }
        
        self.threshold = 0.05  # 5% band
        
    def get_current_allocation(self, balances: Dict, prices: Dict) -> Dict:
        """Calculate current portfolio allocation"""
        btc_value = Decimal(str(balances.get("BTC", 0))) * Decimal(str(prices.get("BTC-USD", 95000)))
        eth_value = Decimal(str(balances.get("ETH", 0))) * Decimal(str(prices.get("ETH-USD", 3500)))
        usd_value = Decimal(str(balances.get("USD", 0)))
        
        total_value = btc_value + eth_value + usd_value
        
        if total_value == 0:
            return {"BTC": 0, "ETH": 0, "USD": 0}
        
        return {
            "BTC": float(btc_value / total_value),
            "ETH": float(eth_value / total_value),
            "USD": float(usd_value / total_value),
            "total_value": float(total_value),
            "values": {
                "BTC": float(btc_value),
                "ETH": float(eth_value),
                "USD": float(usd_value)
            }
        }
    
    def should_rebalance(self, balances: Dict, prices: Dict) -> bool:
        """Check if rebalancing is needed"""
        current = self.get_current_allocation(balances, prices)
        
        for asset in ["BTC", "ETH"]:
            if abs(current[asset] - self.targets[asset]) > self.threshold:
                return True
        
        return False

if __name__ == "__main__":
    print("Rebalancer ready!")
    with open("state/balances.json", "r") as f:
        balances = json.load(f)
    
    prices = {"BTC-USD": 95000, "ETH-USD": 3500}
    rebalancer = PortfolioRebalancer()
    current = rebalancer.get_current_allocation(balances, prices)
    
    print(f"Portfolio Value: ${current['total_value']:,.2f}")
    print(f"BTC: {current['BTC']:.1%}")
    print(f"ETH: {current['ETH']:.1%}")
    print(f"USD: {current['USD']:.1%}")

"""Performance Tracking System"""
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict

class PerformanceTracker:
    """Track portfolio performance"""
    
    def __init__(self):
        self.history_file = "logs/performance_history.jsonl"
        
    def calculate_metrics(self, balances: Dict, prices: Dict) -> Dict:
        """Calculate performance metrics"""
        btc_value = Decimal(str(balances.get("BTC", 0))) * Decimal(str(prices.get("BTC-USD", 0)))
        eth_value = Decimal(str(balances.get("ETH", 0))) * Decimal(str(prices.get("ETH-USD", 0)))
        usd_value = Decimal(str(balances.get("USD", 0)))
        
        total_value = btc_value + eth_value + usd_value
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "total_value": float(total_value),
            "balances": balances,
            "prices": prices,
            "allocations": {
                "BTC": float(btc_value / total_value) if total_value > 0 else 0,
                "ETH": float(eth_value / total_value) if total_value > 0 else 0,
                "USD": float(usd_value / total_value) if total_value > 0 else 0
            }
        }
        
        os.makedirs("logs", exist_ok=True)
        with open(self.history_file, "a") as f:
            f.write(json.dumps(metrics) + "\n")
        
        return metrics

if __name__ == "__main__":
    tracker = PerformanceTracker()
    with open("state/balances.json", "r") as f:
        balances = json.load(f)
    
    prices = {"BTC-USD": 95000, "ETH-USD": 3500}
    metrics = tracker.calculate_metrics(balances, prices)
    
    print(f"Portfolio Value: ${metrics['total_value']:,.2f}")
    print(f"BTC: {metrics['allocations']['BTC']:.1%}")
    print(f"ETH: {metrics['allocations']['ETH']:.1%}")
    print(f"USD: {metrics['allocations']['USD']:.1%}")

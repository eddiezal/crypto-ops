"""Automated Trading Bot"""
import time
import json
from datetime import datetime
from apps.rebalancer.smart_rebalancer import PortfolioRebalancer
from apps.trading.order_executor import OrderExecutor

class CryptoTradingBot:
    """Automated trading bot"""
    
    def __init__(self, mode="simulate"):
        self.mode = mode
        self.rebalancer = PortfolioRebalancer()
        self.executor = OrderExecutor(mode=mode)
        self.stats = {
            "started": datetime.now().isoformat(),
            "cycles": 0,
            "rebalances": 0
        }
    
    def run_cycle(self):
        """Run one trading cycle"""
        print(f"\nCYCLE #{self.stats['cycles'] + 1}")
        print("=" * 40)
        
        with open("state/balances.json", "r") as f:
            balances = json.load(f)
        
        prices = {"BTC-USD": 95000, "ETH-USD": 3500}
        
        current = self.rebalancer.get_current_allocation(balances, prices)
        print(f"Value: ${current['total_value']:,.2f}")
        print(f"BTC: {current['BTC']:.1%} | ETH: {current['ETH']:.1%} | USD: {current['USD']:.1%}")
        
        if self.rebalancer.should_rebalance(balances, prices):
            print("Rebalancing needed!")
            self.stats["rebalances"] += 1
        else:
            print("Portfolio balanced")
        
        self.stats["cycles"] += 1
        
        with open("logs/bot_stats.json", "w") as f:
            json.dump(self.stats, f, indent=2)

if __name__ == "__main__":
    bot = CryptoTradingBot()
    bot.run_cycle()
    print("\nBot cycle complete!")

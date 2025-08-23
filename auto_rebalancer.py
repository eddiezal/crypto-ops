"""Automated Rebalancing Service"""
import time
import json
from datetime import datetime
from execute_rebalance import *

def auto_rebalance():
    """Run rebalancing check every hour"""
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking portfolio...")
            
            with open("state/balances.json", "r") as f:
                balances = json.load(f)
            
            prices = {"BTC-USD": 95000, "ETH-USD": 3500}
            rebalancer = PortfolioRebalancer()
            
            if rebalancer.should_rebalance(balances, prices):
                print("🔄 Rebalancing needed - executing...")
                # Run rebalance logic here
                exec(open("execute_rebalance.py").read())
            else:
                print("✅ Portfolio balanced")
            
            print("💤 Sleeping 1 hour...")
            time.sleep(3600)  # 1 hour
            
        except KeyboardInterrupt:
            print("\n🛑 Auto-rebalancer stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)  # Retry in 1 minute

if __name__ == "__main__":
    print("🤖 AUTO-REBALANCER STARTED")
    print("Press Ctrl+C to stop")
    auto_rebalance()

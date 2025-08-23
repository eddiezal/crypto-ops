"""Master Dashboard"""
import json
from datetime import datetime
from apps.rebalancer.smart_rebalancer import PortfolioRebalancer
from apps.analytics.performance_tracker import PerformanceTracker

def run_dashboard():
    print("=" * 60)
    print("         CRYPTOOPS DASHBOARD")
    print("=" * 60)
    
    with open("state/balances.json", "r") as f:
        balances = json.load(f)
    
    prices = {"BTC-USD": 95000, "ETH-USD": 3500}
    
    rebalancer = PortfolioRebalancer()
    tracker = PerformanceTracker()
    
    current = rebalancer.get_current_allocation(balances, prices)
    metrics = tracker.calculate_metrics(balances, prices)
    
    print(f"\n💰 PORTFOLIO")
    print(f"  Value: ${current['total_value']:,.2f}")
    print(f"  BTC: {balances['BTC']:.4f} @ ${prices['BTC-USD']:,}")
    print(f"  ETH: {balances['ETH']:.4f} @ ${prices['ETH-USD']:,}")
    print(f"  USD: ${balances['USD']:.2f}")
    
    print(f"\n📊 ALLOCATION")
    print(f"  BTC: {current['BTC']:.1%} (target: 65%)")
    print(f"  ETH: {current['ETH']:.1%} (target: 30%)")
    print(f"  USD: {current['USD']:.1%} (target: 5%)")
    
    if rebalancer.should_rebalance(balances, prices):
        print(f"\n⚠️ REBALANCING NEEDED")
    else:
        print(f"\n✅ BALANCED")
    
    try:
        with open("logs/bot_stats.json", "r") as f:
            bot = json.load(f)
        print(f"\n🤖 BOT: {bot.get('cycles', 0)} cycles, {bot.get('rebalances', 0)} rebalances")
    except:
        print(f"\n🤖 BOT: Not running")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    run_dashboard()

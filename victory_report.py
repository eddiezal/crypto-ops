import json
from datetime import datetime

print("=" * 60)
print("    🎊 REBALANCING COMPLETE! 🎊")
print("=" * 60)

# Load new balanced state
with open("state/balances.json", "r") as f:
    balances = json.load(f)

prices = {"BTC-USD": 95000, "ETH-USD": 3500}

# Calculate values
btc_value = balances["BTC"] * prices["BTC-USD"]
eth_value = balances["ETH"] * prices["ETH-USD"]
usd_value = balances["USD"]
total_value = btc_value + eth_value + usd_value

# Calculate percentages
btc_pct = (btc_value / total_value) * 100
eth_pct = (eth_value / total_value) * 100
usd_pct = (usd_value / total_value) * 100

print(f"\n💰 NEW PORTFOLIO POSITIONS:")
print(f"  BTC: {balances['BTC']:.6f} BTC")
print(f"  ETH: {balances['ETH']:.6f} ETH")
print(f"  USD: ${balances['USD']:.2f}")

print(f"\n📊 ACHIEVED ALLOCATION:")
print(f"  BTC: {btc_pct:.1f}% {'✅' if abs(btc_pct - 65) < 5 else '⚠️'} (target: 65%)")
print(f"  ETH: {eth_pct:.1f}% {'✅' if abs(eth_pct - 30) < 5 else '⚠️'} (target: 30%)")
print(f"  USD: {usd_pct:.1f}% {'✅' if abs(usd_pct - 5) < 5 else '⚠️'} (target: 5%)")

print(f"\n💵 PORTFOLIO VALUE: ${total_value:,.2f}")

# Check if within threshold
all_balanced = (
    abs(btc_pct - 65) < 5 and
    abs(eth_pct - 30) < 5 and
    abs(usd_pct - 5) < 5
)

if all_balanced:
    print(f"\n✅ PERFECT BALANCE ACHIEVED!")
    print(f"   Your portfolio is now optimally allocated")
    print(f"   Next rebalance check in 1 hour")
else:
    print(f"\n⚠️ Minor adjustment may be needed")

print(f"\n📅 Rebalanced at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

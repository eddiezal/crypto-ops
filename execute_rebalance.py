"""Execute Rebalancing Orders"""
import json
from decimal import Decimal
from apps.rebalancer.smart_rebalancer import PortfolioRebalancer
from apps.trading.order_executor import OrderExecutor

print("=" * 60)
print("         EXECUTING REBALANCE")
print("=" * 60)

# Load current state
with open("state/balances.json", "r") as f:
    balances = json.load(f)

prices = {"BTC-USD": 95000, "ETH-USD": 3500}

# Initialize rebalancer
rebalancer = PortfolioRebalancer()
current = rebalancer.get_current_allocation(balances, prices)

print(f"\n📊 CURRENT ALLOCATION:")
print(f"  BTC: {current['BTC']:.1%} → Target: 65%")
print(f"  ETH: {current['ETH']:.1%} → Target: 30%")
print(f"  USD: {current['USD']:.1%} → Target: 5%")

# Calculate required trades
total_value = Decimal(str(current['total_value']))

# Target values
target_btc_value = total_value * Decimal("0.65")  # 65%
target_eth_value = total_value * Decimal("0.30")  # 30%
target_usd_value = total_value * Decimal("0.05")  # 5%

# Current values
current_btc_value = Decimal(str(current['values']['BTC']))
current_eth_value = Decimal(str(current['values']['ETH']))
current_usd_value = Decimal(str(current['values']['USD']))

# Calculate differences
btc_diff = target_btc_value - current_btc_value
eth_diff = target_eth_value - current_eth_value
usd_diff = target_usd_value - current_usd_value

print(f"\n💰 REQUIRED CHANGES:")
print(f"  BTC: ${btc_diff:,.2f}")
print(f"  ETH: ${eth_diff:,.2f}")
print(f"  USD: ${usd_diff:,.2f}")

# Generate orders
orders = []

# We need to SELL BTC and BUY ETH
btc_to_sell = abs(btc_diff) / Decimal(str(prices["BTC-USD"]))
eth_to_buy = eth_diff / Decimal(str(prices["ETH-USD"]))

if btc_to_sell >= Decimal("0.001"):  # Min BTC order
    orders.append({
        "product": "BTC-USD",
        "side": "sell",
        "size": float(btc_to_sell.quantize(Decimal("0.00001"))),
        "price": prices["BTC-USD"]
    })

if eth_to_buy >= Decimal("0.01"):  # Min ETH order
    orders.append({
        "product": "ETH-USD",
        "side": "buy",
        "size": float(eth_to_buy.quantize(Decimal("0.001"))),
        "price": prices["ETH-USD"]
    })

print(f"\n📝 ORDERS TO EXECUTE:")
for i, order in enumerate(orders, 1):
    print(f"\n  Order {i}:")
    print(f"    {order['side'].upper()} {order['size']} {order['product'].split('-')[0]}")
    print(f"    @ ${order['price']:,}")
    print(f"    Value: ${order['size'] * order['price']:,.2f}")

# Execute orders
executor = OrderExecutor(mode="simulate")

print(f"\n⚡ EXECUTING...")
for order in orders:
    result = executor.execute_order(order)
    if result["status"] == "filled":
        print(f"  ✅ {order['side'].upper()} {order['size']} {order['product'].split('-')[0]} - FILLED")
    else:
        print(f"  ❌ {order['side'].upper()} {order['size']} {order['product'].split('-')[0]} - {result.get('reason', 'FAILED')}")

# Save new balances
new_balances = {k: float(v) for k, v in executor.balances.items()}

print(f"\n📊 NEW BALANCES:")
print(f"  BTC: {new_balances['BTC']:.6f}")
print(f"  ETH: {new_balances['ETH']:.6f}")
print(f"  USD: ${new_balances['USD']:.2f}")

# Save to state
with open("state/balances_rebalanced.json", "w") as f:
    json.dump(new_balances, f, indent=2)

# Calculate new allocation
new_current = rebalancer.get_current_allocation(new_balances, prices)

print(f"\n📊 NEW ALLOCATION:")
print(f"  BTC: {new_current['BTC']:.1%} (target: 65%)")
print(f"  ETH: {new_current['ETH']:.1%} (target: 30%)")
print(f"  USD: {new_current['USD']:.1%} (target: 5%)")

if abs(new_current['BTC'] - 0.65) < 0.05 and abs(new_current['ETH'] - 0.30) < 0.05:
    print(f"\n✅ PORTFOLIO SUCCESSFULLY REBALANCED!")
else:
    print(f"\n⚠️ Additional rebalancing may be needed")

print("=" * 60)

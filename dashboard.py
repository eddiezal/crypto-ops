print("=" * 56)
print("          CRYPTOOPS SANDBOX DASHBOARD")
print("=" * 56)

from apps.exchange.sandbox_client import CoinbaseSandboxClient
import json

# Get sandbox data
print("\nConnecting to sandbox...")
client = CoinbaseSandboxClient()
balances = client.get_balances()

print("\n💰 SANDBOX POSITIONS (REAL API DATA)")
print(f"  USD:  ${float(balances.get('USD', 0)):>10,.2f}")
print(f"  USDC: ${float(balances.get('USDC', 0)):>10,.2f}")
print(f"  BTC:  {float(balances.get('BTC', 0)):>10.6f} BTC")
print(f"  ETH:  {float(balances.get('ETH', 0)):>10.6f} ETH")

# Estimate value
btc_price = 95000
eth_price = 3500
total = (
    float(balances.get('USD', 0)) + 
    float(balances.get('USDC', 0)) +
    float(balances.get('BTC', 0)) * btc_price +
    float(balances.get('ETH', 0)) * eth_price
)

print(f"\n📊 ESTIMATED VALUE: ${total:,.2f}")
print(f"  (BTC @ ${btc_price:,}, ETH @ ${eth_price:,})")

# Read state file
with open('state/balances.json', 'r') as f:
    state = json.load(f)

print(f"\n📁 STATE FILE:")
print(f"  USD: {state.get('USD', 0)}")
print(f"  BTC: {state.get('BTC', 0)}")
print(f"  ETH: {state.get('ETH', 0)}")

# Check if they match
match = (
    abs(float(state.get('USD', 0)) - float(balances.get('USD', 0))) < 0.01 and
    abs(float(state.get('BTC', 0)) - float(balances.get('BTC', 0))) < 0.01 and
    abs(float(state.get('ETH', 0)) - float(balances.get('ETH', 0))) < 0.01
)

if match:
    print("\n✅ State synchronized with sandbox")
else:
    print("\n⚠️ State not synchronized!")
    print("  Run sync command to fix")

print("=" * 56)

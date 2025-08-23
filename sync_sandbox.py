"""Sync state with Coinbase sandbox"""
from apps.exchange.sandbox_client import CoinbaseSandboxClient
import json

print("Syncing state with sandbox...")

# Get sandbox balances
client = CoinbaseSandboxClient()
balances = client.get_balances()

# Save to state
state = {
    "USD": float(balances.get("USD", 0)),
    "BTC": float(balances.get("BTC", 0)),
    "ETH": float(balances.get("ETH", 0))
}

with open("state/balances.json", "w") as f:
    json.dump(state, f, indent=2)

print(f"\n✅ State synced:")
for k, v in state.items():
    print(f"  {k}: {v}")

# Test reconciliation
from apps.recon.sandbox_recon import reconcile_once
result = reconcile_once(abs_usd=1, pct=0.1)

if result["ok"]:
    print("\n✅ Reconciliation PASSED!")
else:
    print("\n❌ Reconciliation failed - check implementation")

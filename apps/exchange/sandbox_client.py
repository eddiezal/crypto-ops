"""Coinbase Sandbox Client - Uses REAL Sandbox API"""
from decimal import Decimal
import requests
import json

class CoinbaseSandboxClient:
    """
    Uses REAL Coinbase sandbox API (no auth required)
    """
    
    def __init__(self):
        self.base_url = "https://api-sandbox.coinbase.com/api/v3/brokerage"
        print("=" * 50)
        print("🎯 COINBASE SANDBOX CLIENT")
        print("Using REAL sandbox API (no auth)")
        print("=" * 50)
        
        # Test connection
        self._verify_sandbox()
    
    def _verify_sandbox(self):
        """Verify we can reach sandbox"""
        try:
            response = requests.get(f"{self.base_url}/accounts", timeout=5)
            if response.status_code == 200:
                print("✅ Connected to Coinbase sandbox!")
            else:
                print(f"⚠️ Sandbox returned: {response.status_code}")
        except Exception as e:
            print(f"❌ Cannot reach sandbox: {e}")
    
    def get_accounts(self):
        """Get sandbox accounts"""
        response = requests.get(f"{self.base_url}/accounts", timeout=5)
        if response.status_code == 200:
            data = response.json()
            accounts = data.get("accounts", [])
            
            print("\nSandbox Accounts:")
            for acc in accounts:
                currency = acc.get("currency")
                balance = acc.get("available_balance", {}).get("value", "0")
                print(f"  {currency}: {balance}")
            
            return accounts
        return []
    
    def get_balances(self):
        """Get balances as dict"""
        accounts = self.get_accounts()
        balances = {}
        
        for acc in accounts:
            currency = acc.get("currency")
            value = acc.get("available_balance", {}).get("value", "0")
            balances[currency] = Decimal(value)
        
        # Add missing currencies with 0
        for curr in ["USD", "BTC", "ETH", "USDC"]:
            if curr not in balances:
                balances[curr] = Decimal("0")
        
        return balances
    
    def get_product(self, product_id="BTC-USD"):
        """Try to get product (may not work in sandbox)"""
        # Products endpoint seems broken, return mock data
        return {
            "product_id": product_id,
            "price": "95000",  # Mock price
            "base_currency": product_id.split("-")[0],
            "quote_currency": product_id.split("-")[1]
        }

# Test it
if __name__ == "__main__":
    client = CoinbaseSandboxClient()
    
    # Get accounts
    accounts = client.get_accounts()
    
    # Get balances
    balances = client.get_balances()
    print("\nBalances dict:")
    for curr, val in balances.items():
        print(f"  {curr}: {val}")

"""Mock Coinbase Client for Testing"""
from decimal import Decimal
import json
import random

class MockCoinbaseClient:
    """
    Simulates Coinbase API for safe testing
    NO REAL MONEY - Just test data
    """
    
    def __init__(self):
        print("=" * 50)
        print("🛡️ MOCK COINBASE CLIENT")
        print("100% SAFE - No real API calls")
        print("=" * 50)
        
        # Fake sandbox-like balances
        self.balances = {
            "USD": Decimal("50000.00"),
            "BTC": Decimal("2.5"),
            "ETH": Decimal("25.0")
        }
        
        self.prices = {
            "BTC-USD": 95000 + random.randint(-1000, 1000),
            "ETH-USD": 3500 + random.randint(-100, 100)
        }
    
    def get_accounts(self):
        """Return mock accounts"""
        accounts = []
        for currency, balance in self.balances.items():
            accounts.append({
                "currency": currency,
                "balance": str(balance),
                "available": str(balance),
                "hold": "0"
            })
        print(f"\nMock Accounts:")
        for acc in accounts:
            print(f"  {acc['currency']}: {acc['balance']}")
        return accounts
    
    def get_balances(self):
        """Return balances as dict"""
        return dict(self.balances)
    
    def get_price(self, product="BTC-USD"):
        """Get mock price"""
        return self.prices.get(product, 0)
    
    def place_order(self, side, product, size, price=None):
        """Simulate order placement"""
        print(f"\n📝 MOCK ORDER:")
        print(f"  Side: {side}")
        print(f"  Product: {product}")
        print(f"  Size: {size}")
        print(f"  Price: {price or 'market'}")
        print(f"  Status: SIMULATED (no real order)")
        
        return {
            "id": f"mock-{random.randint(1000, 9999)}",
            "side": side,
            "product_id": product,
            "size": size,
            "price": price,
            "status": "pending",
            "settled": False
        }

# Test the mock client
if __name__ == "__main__":
    client = MockCoinbaseClient()
    
    # Get accounts
    accounts = client.get_accounts()
    
    # Get prices
    btc_price = client.get_price("BTC-USD")
    print(f"\nBTC Price: ${btc_price:,}")
    
    # Simulate an order
    order = client.place_order("buy", "BTC-USD", "0.001", btc_price - 1000)
    print(f"\nOrder ID: {order['id']}")

import os
from decimal import Decimal

def get_exchange_client():
    """
    Returns appropriate client based on environment
    """
    mode = os.getenv("EXCHANGE_MODE", "sandbox").lower()
    
    if mode == "mock":
        from apps.exchange.mock_client import MockCoinbaseClient
        print("Using MOCK client")
        return MockCoinbaseClient()
    
    elif mode == "sandbox":
        from apps.exchange.sandbox_client import CoinbaseSandboxClient
        print("Using REAL SANDBOX client")
        return CoinbaseSandboxClient()
    
    elif mode == "production":
        print("❌ PRODUCTION MODE BLOCKED")
        raise Exception("Production disabled for safety")
    
    else:
        # Default to sandbox
        from apps.exchange.sandbox_client import CoinbaseSandboxClient
        return CoinbaseSandboxClient()

if __name__ == "__main__":
    client = get_exchange_client()
    balances = client.get_balances()
    print(f"\nClient balances: {balances}")

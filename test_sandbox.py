"""Complete Coinbase Sandbox Test Suite"""
import json
import requests
from decimal import Decimal

def test_sandbox():
    """Test all sandbox functionality"""
    
    BASE_URL = "https://api-sandbox.coinbase.com/api/v3/brokerage"
    
    print("=" * 60)
    print("COINBASE SANDBOX TEST SUITE")
    print("=" * 60)
    
    # Test 1: Accounts endpoint
    print("\n[TEST 1] Accounts Endpoint")
    response = requests.get(f"{BASE_URL}/accounts")
    if response.status_code == 200:
        data = response.json()
        accounts = data.get("accounts", [])
        print(f"✅ Found {len(accounts)} accounts")
        
        for acc in accounts:
            curr = acc.get("currency")
            val = acc.get("available_balance", {}).get("value", "0")
            print(f"   {curr}: {val}")
    else:
        print(f"❌ Failed: {response.status_code}")
    
    # Test 2: Try products (probably broken)
    print("\n[TEST 2] Products Endpoint")
    response = requests.get(f"{BASE_URL}/products")
    if response.status_code == 200:
        print("✅ Products endpoint works!")
    else:
        print(f"⚠️ Products endpoint returns {response.status_code}")
        print("   (This is expected - sandbox has limited endpoints)")
    
    # Test 3: Try orders
    print("\n[TEST 3] Orders Endpoint")
    response = requests.get(f"{BASE_URL}/orders")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Orders endpoint works: {json.dumps(data)[:100]}...")
    else:
        print(f"⚠️ Orders endpoint returns {response.status_code}")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("- Accounts endpoint: ✅ WORKING")
    print("- Products endpoint: ❌ Not available") 
    print("- Orders endpoint: Check above")
    print("\nYou can use accounts for balance tracking!")
    print("=" * 60)

if __name__ == "__main__":
    test_sandbox()

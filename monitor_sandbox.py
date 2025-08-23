"""Monitor sandbox and alert on changes"""
import time
from apps.exchange.sandbox_client import CoinbaseSandboxClient
import json

def monitor_loop(interval=60):
    """Check sandbox every interval seconds"""
    
    last_balances = None
    
    while True:
        try:
            client = CoinbaseSandboxClient()
            current = client.get_balances()
            
            if last_balances:
                # Check for changes
                for asset in ['USD', 'BTC', 'ETH']:
                    if current.get(asset) != last_balances.get(asset):
                        print(f"⚠️ {asset} changed: {last_balances.get(asset)} → {current.get(asset)}")
            
            last_balances = current
            print(f"✓ Checked at {time.strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(interval)

if __name__ == "__main__":
    print("Starting monitor (Ctrl+C to stop)...")
    monitor_loop(30)  # Check every 30 seconds

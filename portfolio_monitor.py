import time
import json
from datetime import datetime

def monitor_portfolio():
    """Monitor portfolio balance continuously"""
    
    print("🔍 PORTFOLIO MONITOR STARTED")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            with open("state/balances.json", "r") as f:
                b = json.load(f)
            
            total = b["BTC"]*95000 + b["ETH"]*3500 + b["USD"]
            btc_pct = b["BTC"]*95000/total*100
            eth_pct = b["ETH"]*3500/total*100
            usd_pct = b["USD"]/total*100
            
            # Check drift
            btc_drift = abs(btc_pct - 65)
            eth_drift = abs(eth_pct - 30)
            usd_drift = abs(usd_pct - 5)
            max_drift = max(btc_drift, eth_drift, usd_drift)
            
            status = "✅ BALANCED" if max_drift < 5 else "⚠️ DRIFT DETECTED"
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {status} | BTC: {btc_pct:.1f}% | ETH: {eth_pct:.1f}% | USD: {usd_pct:.1f}% | Max Drift: {max_drift:.1f}%")
            
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            print("\n🛑 Monitor stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_portfolio()

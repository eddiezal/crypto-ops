import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for testing
os.environ["MOCK_INGEST"] = "1"
os.environ["DRY_RUN"] = "1"

if __name__ == "__main__":
    print("Testing backfill function...")
    from src.ingest.ingest_binance import backfill
    df = backfill("BTC/USDT", days=7)
    print(f"✓ Backfill returned {len(df)} rows")
    print(df.head())
    
    print("\nTesting metrics API...")
    from src.metrics.api import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    response = client.get("/metrics/equity")
    print(f"✓ API returned status {response.status_code}")
    data = response.json()
    print(f"✓ Equity data has {len(data['days'])} days")

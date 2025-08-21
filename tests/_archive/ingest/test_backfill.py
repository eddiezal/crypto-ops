import os
os.environ.setdefault("MOCK_INGEST", "1")

from src.ingest.ingest_binance import backfill

def test_30d():
    """Test 30-day backfill with mocked data."""
    df = backfill("BTC/USDT", days=30)
    assert not df.empty
    assert df["symbol"].iloc[0] == "BTC/USDT"
    assert df["exchange"].iloc[0] == "binance"
    assert len(df) == 24 * 30  # 30 days of hourly data
    # Check monotonic timestamps
    assert df["ts"].is_monotonic_increasing

def test_symbol_handling():
    """Test different symbol formats."""
    df = backfill("ETH/USDT", days=1)
    assert not df.empty
    assert df["symbol"].iloc[0] == "ETH/USDT"
    assert len(df) == 24  # 1 day of hourly data

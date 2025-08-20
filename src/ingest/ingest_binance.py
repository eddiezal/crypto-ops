from __future__ import annotations

import os
import time
from typing import List

import pandas as pd  # type: ignore[import-not-found]

def backfill(symbol: str, days: int = 30, timeframe: str = "1h") -> pd.DataFrame:
    """Return OHLCV DataFrame for the last `days` (mockable via MOCK_INGEST=1)."""
    if os.getenv("MOCK_INGEST", "0") == "1":
        now = pd.Timestamp.utcnow().floor("h")
        idx = pd.date_range(end=now, periods=24 * days, freq="h")
        df = pd.DataFrame({
            "ts": idx,
            "exchange": "binance",
            "symbol": symbol,
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 0.0,
        })
        return df

    import ccxt  # type: ignore[import-not-found]

    exchange = ccxt.binance()
    since_ms = int((pd.Timestamp.utcnow() - pd.Timedelta(days=days)).timestamp() * 1000)
    ohlcv: List[List[float]] = []
    limit = 1000

    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
        if not batch:
            break
        ohlcv.extend(batch)
        since_ms = int(batch[-1][0]) + 1
        if len(batch) < limit:
            break
        time.sleep(1.0 / float(os.getenv("INGEST_RPS", "5")))

    if not ohlcv:
        return pd.DataFrame(columns=["exchange", "symbol", "ts", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df.insert(0, "exchange", "binance")
    df.insert(1, "symbol", symbol)
    return df

from __future__ import annotations

from fastapi import FastAPI
import pandas as pd

app = FastAPI(title="CryptoOps Metrics")

@app.get("/")
def root():
    return {"message": "CryptoOps Metrics API", "endpoints": ["/metrics/equity", "/docs"]}

@app.get("/metrics/equity")
def equity():
    """Return mock equity curve data."""
    now = pd.Timestamp.utcnow().floor("D")
    idx = pd.date_range(end=now, periods=30, freq="D")
    equity = (100_000 + (pd.Series(range(len(idx))) * 10)).tolist()
    return {
        "days": [d.strftime("%Y-%m-%d") for d in idx],
        "equity": equity,
        "max_drawdown": 0.0
    }

@app.get("/health")
def health():
    return {"status": "healthy", "service": "cryptoops-metrics"}

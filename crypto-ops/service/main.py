from fastapi import FastAPI, Query
from typing import List, Optional, Dict
import os, requests

app = FastAPI(title="CryptoOps Planner", version=os.getenv("PROJECT_VERSION", "0.1.0"))

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/healthz")
def healthz():
    # Simple readiness/liveness endpoint
    return {"status": "ok"}

@app.get("/myip")
def myip():
    # Useful to verify egress/IP and that outbound HTTPS works
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

def parse_overrides(pairs: Optional[List[str]]) -> Optional[Dict[str, float]]:
    if not pairs:
        return None
    out = {}
    for kv in pairs:
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                out[k.strip()] = float(v)
            except Exception:
                pass
    return out or None

@app.get("/plan")
def plan(refresh: bool = False, pair: Optional[List[str]] = Query(None)):
    """
    Produces a plan by calling your in-repo planner.
    - refresh: reserved for future use (pull fresh prices inside container)
    - pair: optional overrides like pair=BTC-USD=125000&pair=SOL-USD=177
    """
    try:
        # Import lazily so import-time DB or config errors don't kill startup
        from apps.rebalancer.main import compute_actions

        overrides = parse_overrides(pair)
        p = compute_actions("trading", override_prices=overrides)
        if not p:
            return {"error": "planner returned empty result"}
        return p
    except Exception as e:
        # Return the error so you can see what the container is missing (e.g., DB)
        return {"error": f"{type(e).__name__}: {e}"}

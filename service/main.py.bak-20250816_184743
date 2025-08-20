# service/main.py
import os, time, hashlib, subprocess, uuid
from typing import Optional, List, Dict
from pathlib import Path

from fastapi import FastAPI, Query
import requests

# Core planner
from apps.rebalancer.main import compute_actions

app = FastAPI(title="CryptoOps Planner", version="1.0")

# --- Helpers -------------------------------------------------------------

def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return "n/a"

def _config_hash() -> str:
    try:
        cfg_path = Path(__file__).resolve().parents[1] / "configs" / "policy.rebalancer.json"
        s = cfg_path.read_text(encoding="utf-8")
    except Exception:
        s = "{}"
    return hashlib.sha256(s.encode()).hexdigest()[:12]

def _mode_payload() -> Dict:
    return {
        "trading_mode": os.getenv("TRADING_MODE", "paper"),   # paper | live
        "coinbase_env": os.getenv("COINBASE_ENV", "sandbox"), # sandbox | prod
        "revision": os.getenv("K_REVISION", "n/a"),
        "code_commit": _git_commit(),
        "config_hash": _config_hash(),
        "run_id": str(uuid.uuid4()),
        "ts": int(time.time())
    }

# --- Routes --------------------------------------------------------------

# Health aliases -> one handler, multiple paths
@app.get("/",            include_in_schema=False, tags=["meta"])
@app.get("/health",      include_in_schema=False, tags=["meta"])
@app.get("/healthz",     include_in_schema=False, tags=["meta"])
@app.get("/readyz",      include_in_schema=False, tags=["meta"])
@app.get("/_ah/health",  include_in_schema=False, tags=["meta"])  # legacy GFE style
def health_all():
    return {"ok": True, **_mode_payload()}

@app.get("/mode", tags=["meta"])
def mode():
    return _mode_payload()

@app.get("/myip", tags=["meta"])
def myip():
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return {"egress_ip": (r.json() or {}).get("ip")}
    except Exception as e:
        return {"error": f"ipify failed: {e.__class__.__name__}"}

@app.get("/plan", tags=["planner"])
def plan(refresh: int = 0, pair: Optional[List[str]] = Query(default=None)):
    """
    Returns the current plan JSON.
    Optional what-if overrides:
      /plan?pair=BTC-USD=125000&pair=SOL-USD=177
    """
    overrides: Dict[str, float] = {}
    for kv in (pair or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                overrides[k.strip()] = float(v)
            except Exception:
                pass

    return compute_actions("trading", override_prices=overrides or None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("service.main:app", host="127.0.0.1", port=8080, reload=True)

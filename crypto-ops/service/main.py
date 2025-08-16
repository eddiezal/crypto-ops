# service/main.py
import os, json, time, hashlib, subprocess
from typing import Optional, List, Dict
from fastapi import FastAPI, Query
import requests

# Core planner
from apps.rebalancer.main import compute_actions

app = FastAPI(title="CryptoOps Planner", version="1.0")

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
        from pathlib import Path
        cfg_path = Path(__file__).resolve().parents[1] / "configs" / "policy.rebalancer.json"
        s = cfg_path.read_text(encoding="utf-8")
    except Exception:
        s = "{}"
    return hashlib.sha256(s.encode()).hexdigest()[:12]

def _mode_payload() -> Dict:
    return {
        "trading_mode": os.getenv("TRADING_MODE", "paper"),     # paper | live
        "coinbase_env": os.getenv("COINBASE_ENV", "sandbox"),   # sandbox | prod
        "revision": os.getenv("K_REVISION", "n/a"),             # Cloud Run revision, if present
        "code_commit": _git_commit(),
        "config_hash": _config_hash(),
        "ts": int(time.time())
    }

@app.get("/healthz")
def healthz():
    return {"ok": True, **_mode_payload()}

@app.get("/mode")
def mode():
    return _mode_payload()

@app.get("/myip")
def myip():
    # Shows the NAT egress IP Cloud Run uses
    r = requests.get("https://api.ipify.org?format=json", timeout=5)
    return {"egress_ip": r.json().get("ip")}

@app.get("/plan")
def plan(refresh: int = 0, pair: Optional[List[str]] = Query(default=None)):
    """
    Returns the current plan JSON. Optional what-if overrides:
    /plan?pair=BTC-USD=125000&pair=SOL-USD=177
    """
    overrides = {}
    for kv in pair or []:
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                overrides[k.strip()] = float(v)
            except:
                pass
    return compute_actions("trading", override_prices=overrides or None)

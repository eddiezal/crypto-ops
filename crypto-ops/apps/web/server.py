import os, sys, json, subprocess
from pathlib import Path
from flask import Flask, jsonify, request

# Keep PYTHONPATH like your local scripts do
BASE = Path(__file__).resolve().parents[2]  # /app
os.environ.setdefault("PYTHONPATH", str(BASE))

# Reuse your compute_actions
from apps.rebalancer.main import compute_actions

def _targets_to_pairs():
    cfg_path = BASE / "configs" / "policy.rebalancer.json"
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        t = cfg.get("targets_trading", {})
        pairs = [f"{k.upper()}-USD" for k in t.keys() if k.upper() != "USD"]
        return sorted(pairs)
    except Exception:
        # Fallback to your default universe
        return ["BTC-USD","ETH-USD","SOL-USD","LINK-USD"]

def _refresh_prices(pairs):
    # Call your existing script inside the container
    script = str(BASE / "scripts" / "fetch_prices_coinbase.py")
    cmd = [sys.executable, script] + pairs
    # Let errors bubble up so the request returns 500 with a useful message
    subprocess.run(cmd, check=True)

app = Flask(__name__)

@app.get("/healthz")
def healthz():
    return {"ok": True}, 200

@app.get("/plan")
def plan():
    # Optional: refresh price table before computing plan
    do_refresh = request.args.get("refresh", "0") in ("1","true","True","yes","y")
    if do_refresh:
        _refresh_prices(_targets_to_pairs())

    # Optional overrides: ?pair=BTC-USD=125000&pair=SOL-USD=177
    overrides = {}
    for key, vals in request.args.lists():
        if key == "pair":
            for kv in vals:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    try:
                        overrides[k.strip()] = float(v)
                    except:
                        pass

    p = compute_actions("trading", override_prices=overrides or None)
    # Always emit JSON (even on errors dicts)
    return jsonify(p if isinstance(p, dict) else {"error": "planner_failed"}), 200

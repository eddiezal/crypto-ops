import os, time, hashlib, subprocess, uuid
from typing import Optional, List, Dict
from pathlib import Path

from fastapi import FastAPI, Query, Header, HTTPException
import requests

from apps.rebalancer.main import compute_actions
from apps.infra.state_gcs import read_json, write_json, append_jsonl, selftest

app = FastAPI(title="CryptoOps Planner", version="1.0")

def _git_commit() -> str:
    try:
        out = subprocess.check_output(["git","rev-parse","--short","HEAD"], stderr=subprocess.DEVNULL)
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
        "trading_mode": os.getenv("TRADING_MODE","paper"),
        "coinbase_env": os.getenv("COINBASE_ENV","sandbox"),
        "revision": os.getenv("K_REVISION","n/a"),
        "code_commit": _git_commit(),
        "config_hash": _config_hash(),
        "run_id": str(uuid.uuid4()),
        "ts": int(time.time()),
    }

def _apply_actions(bal: Dict[str, float], actions: List[Dict]) -> Dict[str, float]:
    b = {k: float(v) for k, v in (bal or {}).items()}
    for a in actions or []:
        sym = a["symbol"]; side = a["side"].lower()
        qty = float(a["qty"]); usd = float(a["usd"])
        if side == "buy":
            b[sym] = float(b.get(sym,0.0)) + qty
            b["USD"] = float(b.get("USD",0.0)) - usd
        elif side == "sell":
            b[sym] = float(b.get(sym,0.0)) - qty
            b["USD"] = float(b.get("USD",0.0)) + usd
    return b

def _nav(bal: Dict[str,float], prices: Dict[str,float]) -> float:
    nav = float((bal or {}).get("USD",0.0))
    for k, q in (bal or {}).items():
        if k.endswith("-USD") and k in (prices or {}):
            nav += float(q) * float(prices[k])
    return nav

# Health aliases
@app.get("/",            include_in_schema=False, tags=["meta"])
@app.get("/health",      include_in_schema=False, tags=["meta"])
@app.get("/healthz",     include_in_schema=False, tags=["meta"])
@app.get("/readyz",      include_in_schema=False, tags=["meta"])
@app.get("/_ah/health",  include_in_schema=False, tags=["meta"])
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

@app.get("/gcs_selftest", tags=["meta"])
def gcs_selftest():
    ok, detail = selftest("state")
    return {"ok": ok, "detail": detail, **_mode_payload()}

@app.get("/plan", tags=["planner"])
def plan(refresh: int = 0, pair: Optional[List[str]] = Query(default=None)):
    overrides: Dict[str, float] = {}
    for kv in (pair or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            try: overrides[k.strip()] = float(v)
            except Exception: pass
    return compute_actions("trading", override_prices=overrides or None)

@app.get("/apply_paper", tags=["planner"])
def apply_paper(commit: int = 0, refresh: int = 0, x_app_key: Optional[str] = Header(None), debug: int = 0):
    expected = os.getenv("APP_KEY")
    if expected and x_app_key != expected:
        raise HTTPException(status_code=401, detail="missing/invalid app key")

    plan = compute_actions("trading")
    actions = plan.get("actions", [])
    prices  = plan.get("prices", {})

    bal_path    = "state/balances.json"
    ts          = int(time.time())
    ts_str      = time.strftime("%Y%m%d_%H%M%S", time.gmtime(ts))
    run_id      = _mode_payload()["run_id"]
    trades_path = f"trades/{ts_str[:8]}.jsonl"
    plan_path   = f"plans/plan_{ts_str}_{run_id}.json"

    balances_before = read_json(bal_path, default=None)
    if balances_before is None:
        balances_before = plan.get("balances", {}) or {}
        balances_before.setdefault("USD", 0.0)

    nav_before = _nav(balances_before, prices)
    balances_after = _apply_actions(balances_before, actions)
    nav_after  = _nav(balances_after, prices)

    summary = {
        "ok": True,
        "dry_run": (commit == 0),
        "actions_count": len(actions),
        "turnover_usd": round(sum(float(a.get("usd", 0)) for a in actions), 2),
        "nav_before": round(nav_before, 2),
        "nav_after": round(nav_after, 2),
    }

    if commit:
        try:
            write_json(plan_path, plan)
            write_json(bal_path, balances_after)

            meta = {
                "ts": ts,
                "run_id": run_id,
                "revision": os.getenv("K_REVISION","n/a"),
                "code_commit": _git_commit(),
                "plan_path": plan_path
            }
            for a in actions:
                rec = dict(meta); rec.update(a)
                append_jsonl(trades_path, rec)

            summary["writes"] = {"balances": bal_path, "trades": trades_path, "plan": plan_path}
        except Exception as e:
            # Log and return a helpful error
            msg = f"GCS write failed: {e.__class__.__name__}: {e}"
            if debug:
                raise HTTPException(status_code=500, detail=msg)
            else:
                raise

    return summary

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("service.main:app", host="127.0.0.1", port=8080, reload=True)

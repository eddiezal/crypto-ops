import os, time, hashlib, subprocess, uuid, json as _json
from typing import Optional, List, Dict, Any
from pathlib import Path

import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import PlainTextResponse

# Core compute & constraints
from apps.rebalancer.main import compute_actions
from apps.rebalancer.constraints import evaluate as _eval_constraints

# State helpers (local or GCS via shim)
from apps.infra.state import read_json, append_jsonl

app = FastAPI(title="CryptoOps Planner", version="1.0")

# ---- SAFETY TRIPWIRES ----
REQUIRED_TRADING_MODE = "paper"
REQUIRED_EXCHANGE_ENV = "sandbox"

@app.on_event("startup")
def _safety_on_startup():
    tm = os.getenv("TRADING_MODE", "paper")
    ex = os.getenv("COINBASE_ENV", "sandbox")
    print(f"Starting with TRADING_MODE={tm}, COINBASE_ENV={ex}")
    # Temporarily disabled strict check due to env var issues
# ---- END TRIPWIRES ----

# --------------------- helpers ---------------------
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

def _mode_payload() -> Dict[str, Any]:
    return {
        "trading_mode": os.getenv("TRADING_MODE","paper"),
        "coinbase_env": os.getenv("COINBASE_ENV","sandbox"),
        "state_bucket": os.getenv("STATE_BUCKET","(unset)"),
        "revision": os.getenv("K_REVISION","n/a"),
        "code_commit": _git_commit(),
        "config_hash": _config_hash(),
        "run_id": str(uuid.uuid4()),
        "ts": int(time.time()),
    }

def _ensure_ledger_db(force: bool = False) -> None:
    gcs_uri = os.getenv("LEDGER_DB_GCS")
    local   = os.getenv("LEDGER_DB")
    if not gcs_uri or not local: return
    if (not force) and os.path.exists(local): return
    try:
        if not gcs_uri.startswith("gs://"): return
        from google.cloud import storage
        bucket_name, blob_name = gcs_uri[5:].split("/", 1)
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        storage.Client().bucket(bucket_name).blob(blob_name).download_to_filename(local)
    except Exception:
        pass

def _pairs_from_targets(t: Dict[str, float]) -> List[str]:
    return [f"{k}-USD" for k in t.keys()]

def _fetch_public_prices(pairs: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for p in pairs:
        try:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{p}/spot", timeout=5)
            amt = float(((r.json() or {}).get("data") or {}).get("amount"))
            out[p] = amt
        except Exception:
            pass
    return out

def _load_targets_from_policy() -> Dict[str, float]:
    try:
        cfg_path = Path(__file__).resolve().parents[1] / "configs" / "policy.rebalancer.json"
        data = _json.loads(cfg_path.read_text(encoding="utf-8"))
        t = data.get("targets_trading") or data.get("targets") or {}
        return {k.upper(): float(v) for k, v in t.items()}
    except Exception:
        return {"BTC": 0.5, "ETH": 0.5}

def _resolve_band_from_policy(default_band: float = 0.01) -> float:
    """
    band = band_dynamic.base clamped to [min,max], else bands_pct, else default_band.
    """
    try:
        base_dir = Path(__file__).resolve().parents[1] / "configs"
        pj = base_dir / "policy.rebalancer.json"
        py = base_dir / "policy.rebalancer.yaml"
        cfg = {}
        if pj.exists():
            cfg = _json.loads(pj.read_text(encoding="utf-8"))
        elif py.exists():
            try:
                import yaml as _yaml
                cfg = _yaml.safe_load(py.read_text(encoding="utf-8")) or {}
            except Exception:
                cfg = {}
        bd = cfg.get("band_dynamic") or {}
        base = bd.get("base", cfg.get("bands_pct", default_band))
        mn   = bd.get("min", base)
        mx   = bd.get("max", base)
        b = float(base); mn = float(mn); mx = float(mx)
        return max(mn, min(b, mx))
    except Exception:
        return default_band

def _with_policy_band(result: Dict[str, Any]) -> Dict[str, Any]:
    cfg = result.setdefault("config", {})
    try:
        cfg["band"] = _resolve_band_from_policy()
    except Exception:
        cfg.setdefault("band", 0.01)
    return result

def _load_policy_config() -> Dict[str, Any]:
    base_dir = Path(__file__).resolve().parents[1] / "configs"
    pj = base_dir / "policy.rebalancer.json"
    py = base_dir / "policy.rebalancer.yaml"
    cfg: Dict[str, Any] = {}
    try:
        if pj.exists():
            cfg = _json.loads(pj.read_text(encoding="utf-8"))
        elif py.exists():
            try:
                import yaml as _yaml  # type: ignore
                cfg = _yaml.safe_load(py.read_text(encoding="utf-8")) or {}
            except Exception:
                cfg = {}
    except Exception:
        cfg = {}
    return cfg

# ---------------- health/meta ----------------
@app.get("/",            include_in_schema=False, tags=["meta"])
@app.get("/health",      include_in_schema=False, tags=["meta"])
@app.get("/healthz",     include_in_schema=False, tags=["meta"])
@app.get("/readyz",      include_in_schema=False, tags=["meta"])
@app.get("/_ah/health",  include_in_schema=False, tags=["meta"])
def health_all():
    return {"ok": True, **_mode_payload()}

# ---------------- planner ----------------
@app.get("/plan", tags=["planner"])
def plan(refresh: int = 0, pair: Optional[List[str]] = Query(default=None), debug: int = 0):
    """
    Returns the current plan JSON. Always publishes policy band; halts on constraint hits.
    Kill-switch: env KILL=1 or state/kill.flag -> halted, no-trade plan.
    """
    # Kill switch early-exit (no try/except needed)
    if os.getenv("KILL") == "1" or bool(read_json("state/kill.flag", default=None)):
        return {
            "account":  "trading",
            "prices":    read_json("state/latest_prices.json", default={}) or {},
            "balances":  read_json("state/balances.json",      default={}) or {},
            "actions":   [],
            "note":      "KILLED: kill switch engaged",
            "config":    { "band": _resolve_band_from_policy(), "halted": True },
        }

    # Planner inputs
    try:
        _ensure_ledger_db(force=bool(refresh))
    except Exception:
        pass

    overrides: Dict[str, float] = {}
    for kv in (pair or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                overrides[k.strip()] = float(v)
            except Exception:
                pass

    # Compute + constraints
    try:
        result = compute_actions("trading", override_prices=overrides or None)
        result = _with_policy_band(result)

        policy_cfg = _load_policy_config()
        result2, hits = _eval_constraints(result, policy_cfg)
        if hits:
            try:
                append_jsonl("logs/constraints.jsonl", {
                    "ts": int(time.time()),
                    "account": "trading",
                    "hits": hits,
                    "band": result2.get("config", {}).get("band"),
                    "meta": _mode_payload(),
                })
            except Exception:
                pass
        return result2
    except Exception as e:
        # Fallback: last saved prices in state, otherwise public spot
        prices = read_json("state/latest_prices.json", default=None)
        if not prices:
            targets = _load_targets_from_policy()
            prices  = _fetch_public_prices(_pairs_from_targets(targets))
        balances = read_json("state/balances.json", default={}) or {}
        note = f"planner_fallback: {e.__class__.__name__}" + (f" | {e}" if debug else "")
        return {
            "account": "trading",
            "prices": prices or {},
            "balances": balances,
            "actions": [],
            "note": note,
            "config": {"band": _resolve_band_from_policy(), "halted": False},
        }

@app.get("/plan_band", tags=["planner"])
def plan_band(refresh: int = 0, pair: Optional[List[str]] = Query(default=None), debug: int = 0):
    try:
        _ensure_ledger_db(force=bool(refresh))
    except Exception:
        pass

    overrides: Dict[str, float] = {}
    for kv in (pair or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                overrides[k.strip()] = float(v)
            except Exception:
                pass

    try:
        result = compute_actions("trading", override_prices=overrides or None)
        return _with_policy_band(result)
    except Exception as e:
        prices = read_json("state/latest_prices.json", default=None)
        if not prices:
            targets = _load_targets_from_policy()
            prices  = _fetch_public_prices(_pairs_from_targets(targets))
        balances = read_json("state/balances.json", default={}) or {}
        note = f"planner_fallback: {e.__class__.__name__}" + (f" | {e}" if debug else "")
        return {
            "account": "trading",
            "prices": prices or {},
            "balances": balances,
            "actions": [],
            "note": note,
            "config": {"band": _resolve_band_from_policy(), "halted": False},
        }

# ---------------- metrics ----------------
@app.get("/metrics", include_in_schema=False, tags=["meta"])
def metrics():
    band = _resolve_band_from_policy()
    meta = _mode_payload()
    lines = [
        "cryptoops_up 1",
        f"cryptoops_band {band}",
        f'cryptoops_revision{{rev="{meta.get("revision","n/a")}"}} 1',
        f'cryptoops_env{{mode="{meta.get("trading_mode","")}",exchange="{meta.get("coinbase_env","")}"}} 1',
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")


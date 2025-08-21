import os, time, hashlib, subprocess, uuid, json as _json
from typing import Optional, List, Dict, Any
from pathlib import Path

import requests
from fastapi import FastAPI, Query, Header, HTTPException

# Core planner + state helpers
from apps.rebalancer.main import compute_actions
from apps.infra.state import read_json, write_json, append_jsonl

app = FastAPI(title="CryptoOps Planner", version="1.0")

# ---- SAFETY TRIPWIRES ----
REQUIRED_TRADING_MODE = "paper"
REQUIRED_EXCHANGE_ENV = "sandbox"

def _assert_safe_env():
    tm = os.getenv("TRADING_MODE", "")
    ex = os.getenv("COINBASE_ENV", "")
    if tm != REQUIRED_TRADING_MODE or ex != REQUIRED_EXCHANGE_ENV:
        raise RuntimeError(f"Unsafe env: TRADING_MODE={tm!r} COINBASE_ENV={ex!r}")

def _refuse_live_creds():
    # Adjust env names if yours differ; tripwire refuses prod secrets entirely.
    live_markers = [
        os.getenv("COINBASE_API_KEY_PROD"),
        os.getenv("COINBASE_API_SECRET_PROD"),
    ]
    if any(live_markers):
        raise RuntimeError("Live exchange credentials detected. Refusing to start.")

@app.on_event("startup")
def _safety_on_startup():
    _refuse_live_creds()
    _assert_safe_env()
# ---- END TRIPWIRES ----

# --------------------- helpers ---------------------
def _git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
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
        "trading_mode": os.getenv("TRADING_MODE", "paper"),
        "coinbase_env": os.getenv("COINBASE_ENV", "sandbox"),
        "state_bucket": os.getenv("STATE_BUCKET", "(unset)"),
        "revision": os.getenv("K_REVISION", "n/a"),
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
        bd = (cfg.get("band_dynamic") or {})
        base = bd.get("base", cfg.get("bands_pct", default_band))
        mn   = bd.get("min", base); mx = bd.get("max", base)
        b = float(base); mn = float(mn); mx = float(mx)
        return max(mn, min(b, mx))
    except Exception:
        return default_band

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
    """Return plan; if DB missing, fall back to last-saved/public prices with no-trade."""
    try: _ensure_ledger_db(force=bool(refresh))
    except Exception: pass

    overrides: Dict[str, float] = {}
    for kv in (pair or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            try: overrides[k.strip()] = float(v)
            except Exception: pass

    try:
        return compute_actions("trading", override_prices=overrides or None)
    except Exception as e:
        prices = read_json("state/latest_prices.json", default=None)
        if not prices:
            targets = _load_targets_from_policy()
            prices = _fetch_public_prices(_pairs_from_targets(targets))
        balances = read_json("state/balances.json", default={}) or {}
        note = f"planner_fallback: {e.__class__.__name__}" + (f" | {e}" if debug else "")
        return {
            "account": "trading",
            "prices": prices or {},
            "balances": balances,
            "actions": [],
            "note": note,
            "config": {"band": None},
            "safety": {
                "mode": os.getenv("TRADING_MODE", ""),
                "exchange": os.getenv("COINBASE_ENV", ""),
                "fallback": True,
                "fallback_source": "state/balances.json",
                "banner": "FAKE / SANDBOX STATE — NOT FROM COINBASE ACCOUNT"
            }
        }

@app.get("/plan_band", tags=["planner"])
def plan_band(refresh: int = 0, pair: Optional[List[str]] = Query(default=None), debug: int = 0):
    try: _ensure_ledger_db(force=bool(refresh))
    except Exception: pass

    overrides: Dict[str, float] = {}
    for kv in (pair or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            try: overrides[k.strip()] = float(v)
            except Exception: pass

    try:
        result = compute_actions("trading", override_prices=overrides or None)
        cfg = result.setdefault("config", {})
        cfg.setdefault("band", _resolve_band_from_policy())
        return result
    except Exception as e:
        prices = read_json("state/latest_prices.json", default=None)
        if not prices:
            targets = _load_targets_from_policy()
            prices = _fetch_public_prices(_pairs_from_targets(targets))
        balances = read_json("state/balances.json", default={}) or {}
        note = f"planner_fallback: {e.__class__.__name__}" + (f" | {e}" if debug else "")
        return {
            "account": "trading",
            "prices": prices or {},
            "balances": balances,
            "actions": [],
            "note": note,
            "config": {"band": _resolve_band_from_policy()},
            "safety": {
                "mode": os.getenv("TRADING_MODE", ""),
                "exchange": os.getenv("COINBASE_ENV", ""),
                "fallback": True,
                "fallback_source": "state/balances.json",
                "banner": "FAKE / SANDBOX STATE — NOT FROM COINBASE ACCOUNT"
            }
        }

# (OPTIONAL) enforce safe env on mutating routes too:
def _auth_guard(x_app_key: Optional[str]):
    expected = os.getenv("APP_KEY")
    if expected and x_app_key != expected:
        raise HTTPException(status_code=401, detail="missing/invalid app key")
    _assert_safe_env()

# Example usage:
# @app.get("/snapshot_now")
# def snapshot_now(..., x_app_key: Optional[str] = Header(None)):
#     _auth_guard(x_app_key)
#     ...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("service.main:app", host="127.0.0.1", port=8080, reload=True)

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
        cfg = result.setdefault("config", {})
        cfg.setdefault("band", _resolve_band_from_policy())
        return result
    except Exception as e:
        prices = read_json("state/latest_prices.json", default=None)
        if not prices:
            targets = _load_targets_from_policy()
            prices = _fetch_public_prices(_pairs_from_targets(targets))
        balances = read_json("state/balances.json", default={}) or {}
        note = f"planner_fallback: {e.__class__.__name__}" + (f" | {e}" if debug else "")
        return {
            "account": "trading",
            "prices": prices or {},
            "balances": balances,
            "actions": [],
            "note": note,
            "config": {"band": _resolve_band_from_policy()},
            "safety": {
                "mode": os.getenv("TRADING_MODE", ""),
                "exchange": os.getenv("COINBASE_ENV", ""),
                "fallback": True,
                "banner": "FAKE / SANDBOX STATE — NOT FROM COINBASE ACCOUNT"
            }
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
        cfg = result.setdefault("config", {})
        cfg.setdefault("band", _resolve_band_from_policy())
        return result
    except Exception as e:
        prices = read_json("state/latest_prices.json", default=None)
        if not prices:
            targets = _load_targets_from_policy()
            prices = _fetch_public_prices(_pairs_from_targets(targets))
        balances = read_json("state/balances.json", default={}) or {}
        note = f"planner_fallback: {e.__class__.__name__}" + (f" | {e}" if debug else "")
        return {
            "account": "trading",
            "prices": prices or {},
            "balances": balances,
            "actions": [],
            "note": note,
            "config": {"band": _resolve_band_from_policy()},
            "safety": {
                "mode": os.getenv("TRADING_MODE", ""),
                "exchange": os.getenv("COINBASE_ENV", ""),
                "fallback": True,
                "banner": "FAKE / SANDBOX STATE — NOT FROM COINBASE ACCOUNT"
            }
        }

@app.get("/snapshot_now", tags=["analytics"])
def snapshot_now(commit: int = 1, x_app_key: Optional[str] = Header(None), debug: int = 0):
    expected = os.getenv("APP_KEY")
    if expected and x_app_key != expected:
        raise HTTPException(status_code=401, detail="missing/invalid app key")

    # Try planner path; fall back to last-saved/public
    try:
        plan_obj = compute_actions("trading")
        prices = plan_obj.get("prices", {}) or {}
        balances = read_json("state/balances.json", default=None) or plan_obj.get("balances", {}) or {}
    except Exception:
        prices = read_json("state/latest_prices.json", default=None)
        if not prices:
            targets = _load_targets_from_policy()
            prices = _fetch_public_prices(_pairs_from_targets(targets))
        balances = read_json("state/balances.json", default={}) or {}
    balances.setdefault("USD", 0.0)

    # NAV compute
    def _nav(bal: Dict[str, float], px: Dict[str, float]) -> float:
        nav = float(bal.get("USD", 0.0))
        for k, q in bal.items():
            if k.endswith("-USD") and k in px:
                nav += float(q) * float(px[k])
        return nav

    nav = _nav(balances, prices or {})
    ts  = int(time.time())

    result = {
        "ok": True,
        "ts": ts,
        "nav": round(nav, 2),
        "commit": bool(commit),
    }

    if commit:
        try:
            append_jsonl("snapshots/daily.jsonl", {
                "ts": ts,
                "nav": round(nav, 2),
                "turnover_usd": 0.0,
                "actions_count": 0,
                "source": "snapshot_now",
                "revision": os.getenv("K_REVISION", "n/a"),
                "commit": True,
            })
        except Exception as e:
            if debug:
                raise HTTPException(status_code=500, detail=f"snapshot write failed: {e.__class__.__name__}: {e}")
    return result
@app.get("/band_debug", tags=["debug"])
def band_debug():
    try:
        base_dir = Path(__file__).resolve().parents[1] / "configs"
        pj = base_dir / "policy.rebalancer.json"
        py = base_dir / "policy.rebalancer.yaml"

        status = {
            "json_path": str(pj),
            "yaml_path": str(py),
            "json_exists": pj.exists(),
            "yaml_exists": py.exists(),
            "config_hash": _config_hash(),
        }

        cfg = {}
        raw = ""
        if pj.exists():
            raw = pj.read_text(encoding="utf-8")
            cfg = _json.loads(raw)
        elif py.exists():
            try:
                import yaml as _yaml
                raw = py.read_text(encoding="utf-8")
                cfg = _yaml.safe_load(raw) or {}
            except Exception as e:
                status["yaml_load_error"] = f"{e.__class__.__name__}: {e}"

        status["raw_head_200"] = raw[:200]
        status["parsed_band_dynamic"] = cfg.get("band_dynamic")
        status["parsed_bands_pct"] = cfg.get("bands_pct")
        status["resolve_band"] = _resolve_band_from_policy()

        return status
    except Exception as e:
        return {"error": f"{e.__class__.__name__}: {e}"}
@app.get("/band_debug", tags=["debug"])
def band_debug():
    try:
        base_dir = Path(__file__).resolve().parents[1] / "configs"
        pj = base_dir / "policy.rebalancer.json"
        py = base_dir / "policy.rebalancer.yaml"

        status = {
            "json_path": str(pj),
            "yaml_path": str(py),
            "json_exists": pj.exists(),
            "yaml_exists": py.exists(),
            "config_hash": _config_hash(),
        }

        cfg = {}
        raw = ""
        if pj.exists():
            raw = pj.read_text(encoding="utf-8")
            cfg = _json.loads(raw)
        elif py.exists():
            try:
                import yaml as _yaml
                raw = py.read_text(encoding="utf-8")
                cfg = _yaml.safe_load(raw) or {}
            except Exception as e:
                status["yaml_load_error"] = f"{e.__class__.__name__}: {e}"

        status["raw_head_200"] = raw[:200]
        status["parsed_band_dynamic"] = cfg.get("band_dynamic")
        status["parsed_bands_pct"] = cfg.get("bands_pct")
        status["resolve_band"] = _resolve_band_from_policy()

        return status
    except Exception as e:
        return {"error": f"{e.__class__.__name__}: {e}"}

def _resolve_band_from_policy(default_band: float = 0.01) -> float:
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
        bd   = (cfg.get("band_dynamic") or {})
        base = bd.get("base", cfg.get("bands_pct", default_band))
        mn   = bd.get("min", base)
        mx   = bd.get("max", base)
        b = float(base); mn = float(mn); mx = float(mx)
        return max(mn, min(b, mx))
    except Exception:
        return default_band


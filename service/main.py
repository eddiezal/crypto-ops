import os, time, hashlib, subprocess, uuid, json as _json
from typing import Optional, List, Dict, Any
from pathlib import Path

import requests
from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse

# Core planner compute & constraints
from apps.rebalancer.main import compute_actions
from apps.rebalancer.constraints import evaluate as _eval_constraints

# State helpers (local or GCS via shim)
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
    # Add real secret names here if/when live creds exist
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
    if not gcs_uri or not local:
        return
    if (not force) and os.path.exists(local):
        return
    try:
        if not gcs_uri.startswith("gs://"):
            return
        from google.cloud import storage  # lazy import
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

def _resolve_band_from_policy(default_band: float = 0.01) -> float:
    """
    band = band_dynamic.base clamped [min,max] OR legacy bands_pct OR default_band
    """
    try:
        base_dir = Path(__file__).resolve().parents[1] / "configs"
        pj = base_dir / "policy.rebalancer.json"
        py = base_dir / "policy.rebalancer.yaml"
        cfg: Dict[str, Any] = {}
        if pj.exists():
            cfg = _json.loads(pj.read_text(encoding="utf-8"))
        elif py.exists():
            try:
                import yaml as _yaml  # type: ignore
                cfg = _yaml.safe_load(py.read_text(encoding="utf-8")) or {}
            except Exception:
                cfg = {}
        bd = (cfg.get("band_dynamic") or {})
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
    """
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
        result = _with_policy_band(result)

        # constraints
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
        # Fallback: try last saved prices in state, otherwise public spot
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
            "config": {"band": _resolve_band_from_policy()},
        }

# ---------------- minimal UI & metrics (read-only) ----------------
@app.get("/dashboard", include_in_schema=False, tags=["meta"])
def dashboard():
    meta = _mode_payload()
    band = _resolve_band_from_policy()
    nav_val = "n/a"; nav_ts = "n/a"
    try:
        recs = read_json("snapshots/daily.jsonl", default=None)
        if isinstance(recs, list) and recs:
            last = recs[-1]
            nav_val = last.get("nav", "n/a")
            ts_i = last.get("ts", None)
            if ts_i:
                from datetime import datetime as _dt
                nav_ts = _dt.utcfromtimestamp(int(ts_i)).strftime("%Y-%m-%d %H:%M:%SZ")
    except Exception:
        pass

    html = f"""
<!doctype html>
<html><head><meta charset="utf-8"><title>CryptoOps Dashboard</title>
<style>
 body {{ font-family: ui-sans-serif, system-ui, Segoe UI, Roboto, Arial; margin: 32px; color:#111 }}
 .card {{ padding:16px; border:1px solid #ddd; border-radius:12px; margin-bottom:16px; }}
 .title {{ font-size:22px; font-weight:700; margin-bottom:8px; }}
 .kv {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
 .muted {{ color:#666; }}
 a {{ color:#0366d6; text-decoration:none }}
</style></head><body>
<h1>CryptoOps — Read-only Dashboard</h1>

<div class="card">
  <div class="title">System</div>
  <div class="kv">Mode: <b>{meta.get("trading_mode","")}</b></div>
  <div class="kv">Environment: <b>{meta.get("coinbase_env","")}</b></div>
  <div class="kv">Revision: <span class="muted">{meta.get("revision","n/a")}</span></div>
  <div class="kv">Config Hash: <span class="muted">{meta.get("config_hash","n/a")}</span></div>
</div>

<div class="card">
  <div class="title">Policy</div>
  <div class="kv">Band: <b>{band:.3f}</b></div>
</div>

<div class="card">
  <div class="title">Analytics</div>
  <div class="kv">Last NAV: <b>{nav_val}</b></div>
  <div class="kv">As of: <span class="muted">{nav_ts}</span></div>
</div>

<p class="muted">Read-only UI. For actions, use your PowerShell / scripts.</p>
</body></html>
"""
    return HTMLResponse(content=html, status_code=200)

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

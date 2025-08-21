# service/main.py
import os, time, math, statistics, hashlib, subprocess, uuid, json as _json
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, Query, Header, HTTPException
import requests, sqlite3

from apps.rebalancer.main import compute_actions
from apps.infra.state import read_json, write_json, append_jsonl

# Optional helpers from state_gcs (we fall back gracefully if unavailable)
try:
    from apps.infra.state import read_ndjson, selftest  # type: ignore
except Exception:  # pragma: no cover
    read_ndjson = None
    selftest = None

app = FastAPI(title="CryptoOps Planner", version="1.6")
# --- conditional debug endpoints (guarded by ENABLE_DEBUG_ENDPOINTS) ---
ENABLE_DEBUG = os.getenv("ENABLE_DEBUG_ENDPOINTS") == "1"

if ENABLE_DEBUG:
    @app.get("/debug/force_500", include_in_schema=False, tags=["debug"])
    def _debug_force_500():
        # Synthetic 500 to exercise monitoring
        raise HTTPException(status_code=500, detail="synthetic 500")

    @app.get("/debug/sleep", include_in_schema=False, tags=["debug"])
    def _debug_sleep(ms: int = 2500):
        time.sleep(max(0, ms) / 1000.0)
        _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"slept_ms": ms}
# --- end conditional debug endpoints ---


# ------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------

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
    _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_
        "trading_mode": os.getenv("TRADING_MODE", "paper"),
        "coinbase_env": os.getenv("COINBASE_ENV", "sandbox"),
        "state_bucket": os.getenv("STATE_BUCKET", "(unset)"),
        "revision": os.getenv("K_REVISION", "n/a"),
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
            b[sym] = float(b.get(sym, 0.0)) + qty
            b["USD"] = float(b.get("USD", 0.0)) - usd
        elif side == "sell":
            b[sym] = float(b.get(sym, 0.0)) - qty
            b["USD"] = float(b.get("USD", 0.0)) + usd
    return b

def _nav(bal: Dict[str, float], prices: Dict[str, float]) -> float:
    nav = float((bal or {}).get("USD", 0.0))
    for k, q in (bal or {}).items():
        if k.endswith("-USD") and k in (prices or {}):
            nav += float(q) * float(prices[k])
    return nav

def _ts_str(ts: Optional[int] = None) -> str:
    ts = ts or int(time.time())
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime(ts))

def _is_sunday(ts: Optional[int] = None) -> bool:
    return time.gmtime(ts or int(time.time())).tm_wday == 6  # Monday=0 ... Sunday=6

def _safe_read_ndjson(path: str) -> List[dict]:
    """Use state_gcs.read_ndjson if present, else parse text manually."""
    if read_ndjson:
        try:
            return read_ndjson(path)  # type: ignore
        except Exception:
            return []
    try:
        from apps.infra.state import read_text
        txt = read_text(path)
        if not txt:
            return []
        out = []
        for ln in txt.splitlines():
            ln = ln.strip()
            if ln:
                try:
                    out.append(_json.loads(ln))
                except Exception:
                    pass
        return out
    except Exception:
        return []

def _load_targets_from_policy() -> Dict[str, float]:
    """Pull target weights from configs/policy.rebalancer.json (fallback to a sane split)."""
    try:
        cfg_path = Path(__file__).resolve().parents[1] / "configs" / "policy.rebalancer.json"
        data = _json.loads(cfg_path.read_text(encoding="utf-8"))
        t = data.get("targets_trading") or data.get("targets") or {}
        _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_k.upper(): float(v) for k, v in t.items()}
    except Exception:
        _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"BTC": 0.45, "ETH": 0.25, "SOL": 0.15, "LINK": 0.15}

def _pairs_from_targets(t: Dict[str, float]) -> List[str]:
    return [f"{k}-USD" for k in t.keys()]

def _fetch_public_prices(pairs: List[str]) -> Dict[str, float]:
    """DB-free fallback using Coinbase public spot prices."""
    out: Dict[str, float] = {}
    for p in pairs:
        try:
            url = f"https://api.coinbase.com/v2/prices/{p}/spot"
            r = requests.get(url, timeout=5)
            amt = float(((r.json() or {}).get("data") or {}).get("amount"))
            out[p] = amt
        except Exception:
            pass
    return out

def _gmtime_iso(ts: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))

# ---------- Ledger DB fetch/inspect -------------------------------------

def _ensure_ledger_db(force: bool = False) -> None:
    """
    If LEDGER_DB_GCS and LEDGER_DB are set and the local file is missing (or force=True),
    download gs://... to the local path (e.g., /tmp/ledger.db).
    """
    gcs_uri = os.getenv("LEDGER_DB_GCS")
    local_path = os.getenv("LEDGER_DB")
    if not gcs_uri or not local_path:
        return
    if (not force) and os.path.exists(local_path):
        return

    try:
        if not gcs_uri.startswith("gs://"):
            return
        rest = gcs_uri[5:]
        bucket_name, blob_name = rest.split("/", 1)

        from google.cloud import storage  # lazy import
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(local_path)
    except Exception:
        # Don't fail requests; /plan has a fallback path, and debug endpoints can diagnose
        pass

def _db_info() -> Dict[str, Any]:
    """Return concise info about the local DB to help debug planner hookup."""
    path = os.getenv("LEDGER_DB")
    d: Dict[str, Any] = {"path": path, "exists": False}
    if not path:
        d["error"] = "LEDGER_DB env not set"
        return d
    try:
        st = os.stat(path)
        d.update({
            "exists": True,
            "size": st.st_size,
            "mtime_utc": _gmtime_iso(int(st.st_mtime)),
        })
    except FileNotFoundError:
        return d
    except Exception as e:
        d["stat_error"] = f"{e.__class__.__name__}: {e}"

    # Try to introspect tables + price columns + sample symbols
    try:
        con = sqlite3.connect(path)
        cur = con.cursor()
        # tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        d["tables"] = [r[0] for r in cur.fetchall()]
        # price columns + counts
        try:
            cols = [r[1] for r in cur.execute("PRAGMA table_info(price)").fetchall()]
            d["price_columns"] = cols
            lower = [c.lower() for c in cols]
            symcol = "symbol" if "symbol" in lower else ("instrument_id" if "instrument_id" in lower else None)

            symbols = {}
            if symcol:
                for s in ("BTC-USD", "ETH-USD", "SOL-USD", "LINK-USD"):
                    try:
                        cur.execute(f"SELECT COUNT(*), MIN(ts), MAX(ts) FROM price WHERE {symcol}=?", (s,))
                        cnt, tmin, tmax = cur.fetchone()
                        symbols[s] = {
                            "count": int(cnt),
                            "min_ts": int(tmin) if tmin is not None else None,
                            "max_ts": int(tmax) if tmax is not None else None,
                        }
                    except Exception:
                        symbols[s] = {"error": "query_failed"}
            d["symbols"] = symbols
        except Exception as e:
            d["price_introspect_error"] = f"{e.__class__.__name__}: {e}"
        finally:
            con.close()
    except Exception as e:
        d["open_error"] = f"{e.__class__.__name__}: {e}"
    return d

# Best‑effort fetch on startup (also done per-request)
@app.on_event("startup")
def _startup_fetch_db():
    _ensure_ledger_db(force=False)

# ------------------------------------------------------------------------
# health/meta
# ------------------------------------------------------------------------

@app.get("/",            include_in_schema=False, tags=["meta"])
@app.get("/health",      include_in_schema=False, tags=["meta"])
@app.get("/healthz",     include_in_schema=False, tags=["meta"])
@app.get("/readyz",      include_in_schema=False, tags=["meta"])
@app.get("/_ah/health",  include_in_schema=False, tags=["meta"])
def health_all():
    _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"ok": True, **_mode_payload()}

@app.get("/mode", tags=["meta"])
def mode():
    return _mode_payload()

@app.get("/myip", tags=["meta"])
def myip():
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"egress_ip": (r.json() or {}).get("ip")}
    except Exception as e:
        _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"error": f"ipify failed: {e.__class__.__name__}"}

@app.get("/gcs_selftest", tags=["meta"])
def gcs_selftest():
    if selftest is None:
        raise HTTPException(status_code=501, detail="selftest helper not available")
    ok, detail = selftest("state")
    _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"ok": ok, "detail": detail, **_mode_payload()}

# --- tiny debug endpoints -----------------------------------------------

@app.get("/planner_force_dbfetch", tags=["debug"])
def planner_force_dbfetch():
    """Force re-download of the ledger DB from LEDGER_DB_GCS to LEDGER_DB."""
    gcs_uri = os.getenv("LEDGER_DB_GCS")
    local = os.getenv("LEDGER_DB")
    if not gcs_uri or not local:
        raise HTTPException(status_code=400, detail="LEDGER_DB_GCS and/or LEDGER_DB not set")
    _ensure_ledger_db(force=True)
    exists = os.path.exists(local)
    size = os.path.getsize(local) if exists else 0
    mtime = _gmtime_iso(int(os.path.getmtime(local))) if exists else None
    _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"ok": True, "status": {"gcs": gcs_uri, "local": local, "downloaded": True, "exists": exists, "size": size, "mtime_utc": mtime}, **_mode_payload()}

@app.get("/planner_debug_db", tags=["debug"])
def planner_debug_db():
    """Return introspection of the local DB file the planner will use."""
    _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"ok": True, "db": _db_info(), **_mode_payload()}

# --- NEW: price appender -------------------------------------------------

@app.get("/prices_append", tags=["ingest"])
def prices_append(
    symbol: Optional[List[str]] = Query(default=None),
    commit: int = 1,
    refresh: int = 1,
    x_app_key: Optional[str] = Header(None),
):
    """
    Append one spot price per symbol into the SQLite 'price' table and upload the updated
    DB back to GCS. Also refresh state/latest_prices.json for analytics fallbacks.
    """
    expected = os.getenv("APP_KEY")
    if expected and x_app_key != expected:
        raise HTTPException(status_code=401, detail="missing/invalid app key")

    _ensure_ledger_db(force=bool(refresh))

    pairs = symbol or ["BTC-USD", "ETH-USD", "SOL-USD", "LINK-USD"]
    prices = _fetch_public_prices(pairs)
    if not prices:
        raise HTTPException(status_code=502, detail="price fetch failed")

    local = os.getenv("LEDGER_DB")
    if not local or not os.path.exists(local):
        raise HTTPException(status_code=500, detail="local DB missing")

    con = sqlite3.connect(local)
    cur = con.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(price)").fetchall()]
    lower = [c.lower() for c in cols]
    if "ts" not in lower:
        con.close()
        raise HTTPException(status_code=500, detail="price.ts missing")

    symcol = "symbol" if "symbol" in lower else ("instrument_id" if "instrument_id" in lower else None)
    pxcol  = "px" if "px" in lower else ("price" if "price" in lower else None)
    if not symcol or not pxcol:
        con.close()
        raise HTTPException(status_code=500, detail="price.{symbol/px} missing")

    ts = int(time.time())
    inserted: List[str] = []
    for s, px in prices.items():
        try:
            cur.execute(f"SELECT 1 FROM price WHERE {symcol}=? AND ts=?", (s, ts))
            if cur.fetchone():
                continue
            cur.execute(
                f"INSERT INTO price(ts, {symcol}, {pxcol}, source) VALUES (?, ?, ?, ?)",
                (ts, s, float(px), "cb_spot"),
            )
            inserted.append(s)
        except Exception as e:
            inserted.append(f"{s}:ERR:{e.__class__.__name__}")
    con.commit()
    con.close()

    # Upload back to GCS (best-effort)
    if commit:
        gcs_uri = os.getenv("LEDGER_DB_GCS")
        try:
            if gcs_uri and gcs_uri.startswith("gs://"):
                from google.cloud import storage
                bucket_name, blob_name = gcs_uri[5:].split("/", 1)
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                # try rename flow for atomic swap
                try:
                    tmp_blob = bucket.blob(blob_name + ".tmp")
                    tmp_blob.upload_from_filename(local)
                    bucket.rename_blob(tmp_blob, new_name=blob_name)
                except Exception:
                    # fallback: direct upload to final
                    blob = bucket.blob(blob_name)
                    blob.upload_from_filename(local)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"GCS upload failed: {e.__class__.__name__}: {e}")

        # refresh analytics fallback
        try:
            write_json("state/latest_prices.json", prices)
        except Exception:
            pass

    _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"ok": True, "ts": ts, "inserted": inserted, "prices": prices, **_mode_payload()}

# ------------------------------------------------------------------------
# plan + paper apply
# ------------------------------------------------------------------------

@app.get("/plan", tags=["planner"])
def plan(refresh: int = 0, pair: Optional[List[str]] = Query(default=None), debug: int = 0):
    """
    Returns the current plan JSON.
    If the planner's DB is unavailable, returns a no-trade fallback with prices from GCS or Coinbase.
    Optional what-if overrides:
      /plan?pair=BTC-USD=125000&pair=SOL-USD=177
    """
    _ensure_ledger_db(force=bool(refresh))

    overrides: Dict[str, float] = {}
    for kv in (pair or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                overrides[k.strip()] = float(v)
            except Exception:
                pass

    try:
        return compute_actions("trading", override_prices=overrides or None)
    except Exception as e:
        # Fallback: try last saved prices in GCS, otherwise public spot
        prices = read_json("state/latest_prices.json", default=None)
        if not prices:
            targets = _load_targets_from_policy()
            prices = _fetch_public_prices(_pairs_from_targets(targets))
        balances = read_json("state/balances.json", default={}) or {}
        note = f"planner_fallback: {e.__class__.__name__}"
        if debug:
            note += f" | {e}"
        _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_
            "account": "trading",
            "prices": prices or {},
            "balances": balances,
            "actions": [],
            "note": note,
            "config": {"band": None},
        }

def _append_snapshots(ts: int, nav_before: float, nav_after: float, turnover_usd: float, actions_count: int, source: str):
    rec = {
        "ts": ts,
        "nav_before": round(nav_before, 2),
        "nav": round(nav_after, 2),
        "turnover_usd": round(turnover_usd, 2),
        "actions_count": int(actions_count),
        "source": source,
        "revision": os.getenv("K_REVISION", "n/a"),
        "commit": True,
    }
    append_jsonl("snapshots/daily.jsonl", rec)
    if _is_sunday(ts):
        append_jsonl("snapshots/weekly.jsonl", rec)

@app.get("/apply_paper", tags=["planner"])
def apply_paper(
    commit: int = 0,
    refresh: int = 0,
    x_app_key: Optional[str] = Header(None),
    debug: int = 0
):
    # Optional header-based auth (only enforced if APP_KEY is set)
    expected = os.getenv("APP_KEY")
    if expected and x_app_key != expected:
        raise HTTPException(status_code=401, detail="missing/invalid app key")

    _ensure_ledger_db(force=bool(refresh))

    # Get plan (fail => 503 for commit, fallback for dry-run)
    try:
        plan_obj = compute_actions("trading")
    except Exception as e:
        if commit:
            raise HTTPException(status_code=503, detail=f"planner unavailable: {e.__class__.__name__}")
        else:
            prices = read_json("state/latest_prices.json", default=None)
            if not prices:
                targets = _load_targets_from_policy()
                prices = _fetch_public_prices(_pairs_from_targets(targets))
            balances_before = read_json("state/balances.json", default={}) or {}
            nav = _nav(balances_before, prices or {})
            msg = f"planner_fallback: {e.__class__.__name__}"
            if debug:
                msg += f" | {e}"
            _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_
                "ok": True,
                "dry_run": True,
                "actions_count": 0,
                "turnover_usd": 0,
                "nav_before": round(nav, 2),
                "nav_after": round(nav, 2),
                "note": msg,
            }

    actions = plan_obj.get("actions", [])
    prices  = plan_obj.get("prices", {}) or {}

    bal_path    = "state/balances.json"
    ts          = int(time.time())
    ts_str      = _ts_str(ts)
    run_id      = _mode_payload()["run_id"]
    trades_path = f"trades/{ts_str[:8]}.jsonl"
    plan_path   = f"plans/plan_{ts_str}_{run_id}.json"

    # Read balances (tolerant for dry-run)
    balances_before = None
    gcs_read_ok = True
    try:
        try:
            balances_before = read_json(bal_path, default=None)
        except TypeError:
            balances_before = read_json(bal_path)
    except Exception:
        gcs_read_ok = False
        if commit == 1:
            raise

    if balances_before is None:
        balances_before = plan_obj.get("balances", {}) or {}
        balances_before.setdefault("USD", 0.0)

    nav_before = _nav(balances_before, prices)
    balances_after = _apply_actions(balances_before, actions)
    nav_after  = _nav(balances_after, prices)

    turnover = sum(float(a.get("usd", 0)) for a in actions)
    summary = {
        "ok": True,
        "dry_run": (commit == 0),
        "actions_count": len(actions),
        "turnover_usd": round(turnover, 2),
        "nav_before": round(nav_before, 2),
        "nav_after": round(nav_after, 2),
    }
    if commit == 0 and not gcs_read_ok:
        summary["note"] = "GCS read failed; used plan balances for dry-run."

    if commit:
        try:
            write_json(plan_path, plan_obj)
            write_json(bal_path, balances_after)
            if prices:
                write_json("state/latest_prices.json", prices)

            if actions:
                meta = {
                    "ts": ts,
                    "run_id": run_id,
                    "revision": os.getenv("K_REVISION", "n/a"),
                    "code_commit": _git_commit(),
                    "plan_path": plan_path
                }
                for a in actions:
                    rec = dict(meta); rec.update(a)
                    append_jsonl(trades_path, rec)

            _append_snapshots(
                ts=ts,
                nav_before=nav_before,
                nav_after=nav_after,
                turnover_usd=turnover,
                actions_count=len(actions),
                source="apply_paper"
            )

            summary["writes"] = {
                "balances": bal_path,
                "trades": trades_path,
                "plan": plan_path,
                "latest_prices": "state/latest_prices.json",
                "snapshots_daily": "snapshots/daily.jsonl",
                "snapshots_weekly": "snapshots/weekly.jsonl",
            }
        except Exception as e:
            msg = f"GCS write failed: {e.__class__.__name__}: {e}"
            if debug:
                raise HTTPException(status_code=500, detail=msg)
            raise

    return summary

# ------------------------------------------------------------------------
# snapshots + analytics
# ------------------------------------------------------------------------

@app.get("/snapshot_now", tags=["analytics"])
def snapshot_now(commit: int = 0, x_app_key: Optional[str] = Header(None), debug: int = 0):
    """
    Record a NAV snapshot using current balances and prices (no trade).
    Fallback if planner DB is unavailable.
    """
    expected = os.getenv("APP_KEY")
    if expected and x_app_key != expected:
        raise HTTPException(status_code=401, detail="missing/invalid app key")

    _ensure_ledger_db(force=False)

    try:
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

        nav = _nav(balances, prices or {})
        ts  = int(time.time())

        if commit:
            rec = {
                "ts": ts,
                "nav_before": round(nav, 2),
                "nav": round(nav, 2),
                "turnover_usd": 0.0,
                "actions_count": 0,
                "source": "snapshot_now",
                "revision": os.getenv("K_REVISION", "n/a"),
                "commit": True,
            }
            append_jsonl("snapshots/daily.jsonl", rec)
            if _is_sunday(ts):
                append_jsonl("snapshots/weekly.jsonl", rec)

        _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"ok": True, "committed": bool(commit), "ts": ts, "nav": round(nav, 2)}
    except Exception as e:
        if debug:
            raise HTTPException(status_code=500, detail=f"snapshot failed: {e.__class__.__name__}: {e}")
        raise

def _equity_series(days: int = 365) -> List[Dict[str, float]]:
    rows = _safe_read_ndjson("snapshots/daily.jsonl")
    if not rows:
        return []
    rows = sorted(rows, key=lambda r: int(r.get("ts", 0)))
    cutoff = int(time.time()) - days * 86400
    out = []
    for r in rows:
        ts = int(r.get("ts", 0))
        if ts >= cutoff:
            nav = r.get("nav")
            if nav is None:
                nav = r.get("nav_after", 0.0)
            out.append({"ts": ts, "nav": float(nav)})
    return out

def _metrics_from_series(series: List[Dict[str, float]]) -> Dict[str, float]:
    if len(series) < 2:
        last = series[-1]["nav"] if series else None
        _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_
            "points": len(series),
            "last_nav": round(last, 2) if last is not None else None,
            "note": "Not enough data for statistics",
        }

    ts0, nav0 = series[0]["ts"], series[0]["nav"]
    tsN, navN = series[-1]["ts"], series[-1]["nav"]
    days = max(1, round((tsN - ts0) / 86400))

    rets = []
    for i in range(1, len(series)):
        n0 = series[i - 1]["nav"]
        n1 = series[i]["nav"]
        if n0 > 0:
            rets.append((n1 / n0) - 1.0)

    if len(rets) >= 2:
        mu_d = statistics.mean(rets)
        sd_d = statistics.pstdev(rets) if len(rets) > 1 else 0.0
        vol_ann = (sd_d * math.sqrt(365.0)) if sd_d > 0 else 0.0
        sharpe = (mu_d / sd_d * math.sqrt(365.0)) if sd_d > 0 else None
    else:
        mu_d, vol_ann, sharpe = 0.0, 0.0, None

    total_ret = (navN / nav0) - 1.0 if nav0 > 0 else None
    cagr = ((navN / nav0) ** (365.0 / days) - 1.0) if (nav0 > 0 and days >= 1) else None

    peak = -1e18
    maxdd = 0.0
    for p in series:
        v = p["nav"]
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v / peak) - 1.0
            if dd < maxdd:
                maxdd = dd

    _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_
        "points": len(series),
        "first_ts": ts0,
        "last_ts": tsN,
        "days": days,
        "first_nav": round(nav0, 2),
        "last_nav": round(navN, 2),
        "total_return": round(total_ret, 6) if total_ret is not None else None,
        "cagr": round(cagr, 6) if cagr is not None else None,
        "vol_ann": round(vol_ann, 6),
        "sharpe": round(sharpe, 4) if sharpe is not None else None,
        "max_drawdown": round(maxdd, 6),
    }

@app.get("/equity_curve", tags=["analytics"])
def equity_curve(days: int = 365):
    series = _equity_series(days=days)
    _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"ok": True, "days": days, "series": series, **_mode_payload()}

@app.get("/metrics", tags=["analytics"])
def metrics(days: int = 365):
    series = _equity_series(days=days)
    m = _metrics_from_series(series)
    _ret_ = \1
try:
    _ = _ret_.setdefault("config", {})
    _["band"] = _resolve_band_from_policy()
except Exception:
    pass
return _ret_"ok": True, "days": days, "metrics": m, **_mode_payload()}

# ------------------------------------------------------------------------
# dev: run local
# ------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    # Local dev only; Cloud Run uses the Procfile (uvicorn on 0.0.0.0:$PORT)
    uvicorn.run("service.main:app", host="127.0.0.1", port=8080, reload=True)

# --- CTO patch: ensure POST is allowed for /apply_paper ---
try:
    app.add_api_route("/apply_paper", apply_paper, methods=["POST"])
except Exception as _e:
    # If it's already added or symbols differ, ignore.
    pass
# --- end patch ---
from fastapi import Body  # ensure import is present at the top of file

@app.post("/prices_append", tags=["ingest"])
def prices_append_post(payload: dict = Body(default=None), x_app_key: Optional[str] = Header(None)):
    # If payload supplies symbols, adapt to existing handler
    # Expected payload: { "symbol": ["BTC-USD","ETH-USD"] } OR {} to use defaults
    symbols = None
    if payload and isinstance(payload.get("symbol"), list):
        symbols = payload["symbol"]
    return prices_append(symbol=symbols, commit=1, refresh=1, x_app_key=x_app_key)

@app.post("/apply_paper", tags=["planner"])
def apply_paper_post(commit: int = 0, refresh: int = 0, x_app_key: Optional[str] = Header(None)):
    return apply_paper(commit=commit, refresh=refresh, x_app_key=x_app_key, debug=0)
# ---- band resolver (appended by ops) ----
from pathlib import Path as _Path
import json as _json
try:
    import yaml as _yaml  # optional
except Exception:
    _yaml = None

def _resolve_band_from_policy(default_band: float = 0.01) -> float:
    """
    band = band_dynamic.base (clamped to min/max) OR bands_pct OR default_band
    """
    try:
        base_dir = _Path(__file__).resolve().parents[1] / "configs"
        pj = base_dir / "policy.rebalancer.json"
        py = base_dir / "policy.rebalancer.yaml"
        cfg = {}
        if pj.exists():
            cfg = _json.loads(pj.read_text(encoding="utf-8"))
        elif py.exists() and _yaml:
            cfg = _yaml.safe_load(py.read_text(encoding="utf-8")) or {}

        bd = (cfg.get("band_dynamic") or {})
        base = bd.get("base", cfg.get("bands_pct", default_band))
        mn = bd.get("min", base)
        mx = bd.get("max", base)

        b  = float(base)
        mn = float(mn)
        mx = float(mx)
        return max(mn, min(b, mx))
    except Exception:
        return default_band
# ---- end band resolver ----



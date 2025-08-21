        result = compute_actions("trading", override_prices=overrides or None)
        cfg = result.setdefault("config", {})
        cfg["band"] = _resolve_band_from_policy()
        return result@app.get("/",            include_in_schema=False, tags=["meta"])
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
        result = compute_actions("trading", override_prices=overrides or None)
        cfg = result.setdefault("config", {})
        cfg["band"] = _resolve_band_from_policy()
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
        cfg["band"] = _resolve_band_from_policy()
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
        cfg["band"] = _resolve_band_from_policy()
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
        cfg["band"] = _resolve_band_from_policy()
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





# --- helper: force policy band into any compute_actions result
def _with_policy_band(result: Dict[str, Any]) -> Dict[str, Any]:
    try:
        cfg = result.setdefault("config", {})
        cfg["band"] = _resolve_band_from_policy()
    except Exception:
        pass
    return result

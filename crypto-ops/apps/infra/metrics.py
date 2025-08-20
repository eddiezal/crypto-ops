# apps/infra/metrics.py
import json, math, statistics, datetime as dt
from typing import Dict, List
from .state_gcs import read_text, read_json, write_json, append_jsonl

def _utc_date_str(): return dt.datetime.utcnow().strftime("%Y-%m-%d")

def _split_bal(bal):
    usd = float(bal.get("USD",0.0))
    qty = {k: float(v) for k,v in bal.items() if k!="USD"}
    return usd, qty

def _nav(bal, prices):
    usd, qty = _split_bal(bal)
    crypto = sum(qty.get(s,0.0)*float(prices.get(s,0.0)) for s in qty.keys())
    return usd+crypto, crypto, qty

def _read_jsonl(path):
    t = read_text(path)
    if not t: return []
    out=[]
    for line in t.splitlines():
        line=line.strip()
        if not line: continue
        try: out.append(json.loads(line))
        except: pass
    return out

def record_daily(prices, balances, code_commit, config_hash):
    day = _utc_date_str()
    nav, crypto, qty = _nav(balances, prices)

    base = read_json("metrics/base.json")
    if base is None:
        base = {"date": day, "usd": float(balances.get("USD",0.0)), "qty": qty}
        write_json("metrics/base.json", base)

    rec = {
        "date": day, "nav": nav, "usd": float(balances.get("USD",0.0)),
        "crypto_val": crypto, "prices": {k: float(prices.get(k,0.0)) for k in sorted(prices.keys())},
        "qty": qty, "code_commit": code_commit, "config_hash": config_hash
    }
    append_jsonl("metrics/nav_daily.jsonl", rec)
    return rec

def _series_nav(rows): return [float(r["nav"]) for r in rows]

def _hodl_nav(prices, base):
    usd = float(base.get("usd",0.0))
    qty = {k: float(v) for k,v in (base.get("qty") or {}).items()}
    crypto = sum(qty.get(s,0.0)*float(prices.get(s,0.0)) for s in qty.keys())
    return usd + crypto

def _rets(nav):
    if len(nav)<2: return []
    out=[]; prev=nav[0]
    for x in nav[1:]:
        if prev>0: out.append(x/prev - 1.0)
        prev=x
    return out

def _stats(nav):
    rets = _rets(nav); n=len(rets)
    if n==0: return {"n_days":0}
    mu = sum(rets)/n
    sig = statistics.stdev(rets) if n>1 else 0.0
    ann = math.sqrt(365.0)
    sharpe = (mu/sig)*ann if sig>0 else None
    vol = sig*ann
    cagr = (nav[-1]/nav[0])**(365.0/max(n,1)) - 1.0 if nav[0]>0 else None
    peak=nav[0]; max_dd=0.0
    for x in nav:
        peak=max(peak,x)
        dd=(x/peak - 1.0) if peak>0 else 0.0
        max_dd=min(max_dd, dd)
    return {"n_days":n,"nav_start":nav[0],"nav_end":nav[-1],"cagr":cagr,"vol_ann":vol,"sharpe_ann":sharpe,"max_drawdown":max_dd}

def compute_summary(window_days=365):
    rows = _read_jsonl("metrics/nav_daily.jsonl")
    if not rows: return {"note":"no daily records yet"}
    rows.sort(key=lambda r: r.get("date",""))
    rows = rows[-window_days:] if window_days and len(rows)>window_days else rows
    strat = _series_nav(rows); strat_stats = _stats(strat)
    base = read_json("metrics/base.json") or {"usd":0.0,"qty":{}}
    hodl = [_hodl_nav(r.get("prices",{}), base) for r in rows]; hodl_stats=_stats(hodl)
    return {"window_days":window_days,"records":len(rows),"strategy":strat_stats,"hodl":hodl_stats}

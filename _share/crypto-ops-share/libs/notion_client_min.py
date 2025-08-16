import os, json, urllib.request

NOTION_VERSION = "2022-06-28"

def _headers():
    token = os.getenv("NOTION_TOKEN","")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }

def _post(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, resp.read().decode("utf-8")

def _get(url: str):
    req = urllib.request.Request(url, headers=_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, resp.read().decode("utf-8")

def post_run(bot: str, decision: str, notional_usd: float=0.0, message: str="", logs_url: str=""):
    runs_db = os.getenv("NOTION_RUNS_DB","")
    token = os.getenv("NOTION_TOKEN","")
    if not (runs_db and token):
        print("[post_run] Notion env missing; skipping.")
        return None
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    payload = {
      "parent": {"database_id": runs_db},
      "properties": {
        "Name": {"title":[{"type":"text","text":{"content": f"{bot} {decision} {now[:19]}Z"}}]},
        "Bot": {"select": {"name": bot}},
        "Project": {"rich_text":[{"type":"text","text":{"content": os.getenv("PROJECT_NAME","default")}}]},
        "Start": {"date":{"start": now}},
        "End": {"date":{"start": now}},
        "Decision": {"select":{"name": decision}},
        "Notional (USD)": {"number": float(notional_usd)},
        "Message": {"rich_text":[{"type":"text","text":{"content": message[:1900]}}]},
        "Logs URL": {"url": logs_url or ""}
      }
    }
    try:
        status, body = _post("https://api.notion.com/v1/pages", payload)
        print("[post_run]", status, body[:160])
        return status, body
    except Exception as e:
        print("[post_run] Exception:", e)
        return None

def post_snapshot(nav_usd: float, vault_pct: float, cash_pct: float, trading_pct: float, pnl_1d: float=0.0, fees_1d: float=0.0):
    snap_db = os.getenv("NOTION_SNAPSHOTS_DB","")
    token = os.getenv("NOTION_TOKEN","")
    if not (snap_db and token):
        print("[post_snapshot] Notion env missing; skipping.")
        return None
    import datetime
    today = datetime.date.today().isoformat()
    payload = {
      "parent": {"database_id": snap_db},
      "properties": {
        "Name": {"title":[{"type":"text","text":{"content": f"Snapshot {today}"}}]},
        "Date": {"date":{"start": today}},
        "NAV (USD)": {"number": float(nav_usd)},
        "Vault %": {"number": float(vault_pct)},
        "Cash %": {"number": float(cash_pct)},
        "Trading %": {"number": float(trading_pct)},
        "PnL 1d": {"number": float(pnl_1d)},
        "Fees (1d)": {"number": float(fees_1d)}
      }
    }
    try:
        status, body = _post("https://api.notion.com/v1/pages", payload)
        print("[post_snapshot]", status, body[:160])
        return status, body
    except Exception as e:
        print("[post_snapshot] Exception:", e)
        return None

def check_database(db_id: str):
    token = os.getenv("NOTION_TOKEN","")
    if not (token and db_id):
        print("[check_database] Missing token or DB id")
        return None
    try:
        status, body = _get(f"https://api.notion.com/v1/databases/{db_id}")
        print("[check_database]", status, body[:160])
        return status, body
    except Exception as e:
        print("[check_database] Exception:", e)
        return None

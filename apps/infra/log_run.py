import json, sqlite3, time
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DB = BASE / "data" / "ledger.db"

def ensure(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS run_log(
      run_id TEXT PRIMARY KEY,
      ts INTEGER,
      account TEXT,
      actions INT,
      buy_usd REAL,
      sell_usd REAL,
      band REAL,
      nav REAL,
      code_commit TEXT,
      config_hash TEXT,
      profile TEXT,
      image TEXT,
      mode TEXT,
      env TEXT
    );
    """)

def nav_from(plan: dict) -> float:
    p = plan.get("prices", {}) or {}
    b = plan.get("balances", {}) or {}
    nav = 0.0
    for k,v in b.items():
        if k == "USD":
            nav += float(v or 0.0)
        else:
            nav += float(v or 0.0) * float(p.get(k,0.0))
    return nav

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-file", required=True)
    args = ap.parse_args()

    plan = json.load(open(args.plan_file,"r",encoding="utf-8"))
    ver  = plan.get("version", {})
    run_id = ver.get("run_id") or str(int(time.time()))

    actions = plan.get("actions") or []
    buys  = sum(a.get("usd",0) for a in actions if a.get("usd",0)>0)
    sells = sum(-a.get("usd",0) for a in actions if a.get("usd",0)<0)

    conn = sqlite3.connect(DB)
    try:
        ensure(conn)
        conn.execute("""
          INSERT OR REPLACE INTO run_log(run_id, ts, account, actions, buy_usd, sell_usd, band, nav,
                                         code_commit, config_hash, profile, image, mode, env)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            run_id,
            int(ver.get("ts") or time.time()),
            plan.get("account","trading"),
            int(len(actions)),
            float(buys or 0.0),
            float(sells or 0.0),
            float(plan.get("config",{}).get("band") or 0.0),
            float(nav_from(plan)),
            ver.get("code_commit","unknown"),
            ver.get("config_hash","unknown"),
            ver.get("profile","(unset)"),
            ver.get("image","n/a"),
            ver.get("trading_mode","paper"),
            ver.get("env","sandbox"),
        ))
        conn.commit()
    finally:
        conn.close()
    print(f"Logged run_id={run_id} actions={len(actions)}")

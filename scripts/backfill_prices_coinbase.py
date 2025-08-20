import sys, json, datetime, time, urllib.request, sqlite3
from libs.db import get_conn

API = "https://api.coinbase.com/v2/prices/{pair}/spot?date={date}"

def fetch(pair, date_str):
    url = API.format(pair=pair, date=date_str)
    with urllib.request.urlopen(url) as r:
        data = json.load(r)
        return float(data["data"]["amount"])

if __name__ == "__main__":
    pairs = ["BTC-USD","ETH-USD","SOL-USD","LINK-USD"]
    days = int(sys.argv[1]) if len(sys.argv)>1 else 120   # default 120 days
    today = datetime.date.today()

    conn = get_conn(); cur = conn.cursor()
    for p in pairs:
        # ensure instrument exists
        cur.execute("INSERT OR IGNORE INTO instrument(id,symbol,kind) VALUES(?,?,?)",(p,p,"crypto"))
        for d in range(days, 0, -1):
            day = today - datetime.timedelta(days=d)
            ds = day.strftime("%Y-%m-%d")
            try:
                px = fetch(p, ds)
            except Exception as e:
                print("skip", p, ds, e); continue
            ts = ds + " 23:59:59"
            # UPSERT: replace existing row for that day/symbol
            cur.execute("""
                INSERT INTO price(ts,instrument_id,px,source) VALUES(?,?,?,?)
                ON CONFLICT(ts, instrument_id) DO UPDATE SET
                    px=excluded.px,
                    source=excluded.source
            """, (ts, p, px, "coinbase_hist"))
            # gentle throttle to avoid rate limits
            time.sleep(0.08)
        print("backfilled:", p)
    conn.commit()
    print("done.")

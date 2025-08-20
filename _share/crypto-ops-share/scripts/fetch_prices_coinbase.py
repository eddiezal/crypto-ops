import json, sys, urllib.request, datetime
from libs.db import get_conn

API = "https://api.coinbase.com/v2/prices/{pair}/spot"

def fetch(pair):
    with urllib.request.urlopen(API.format(pair=pair)) as r:
        data = json.load(r)
        return float(data["data"]["amount"])

if __name__ == "__main__":
    pairs = sys.argv[1:] or ["BTC-USD","ETH-USD","SOL-USD","LINK-USD"]
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn(); cur = conn.cursor()
    for p in pairs:
        px = fetch(p)
        cur.execute("INSERT OR IGNORE INTO instrument(id,symbol,kind) VALUES(?,?,?)",(p,p,"crypto"))
        cur.execute("INSERT INTO price(ts,instrument_id,px,source) VALUES(?,?,?,?)",(ts,p,px,"coinbase"))
        print(f"{p}={px}")
    conn.commit()

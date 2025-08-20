import sqlite3, sys, os, time
db = r"F:\CryptoOps\crypto-ops\data\ledger.db"
print("DB:", db, "exists:", os.path.exists(db), "size:", os.path.getsize(db) if os.path.exists(db) else 0)
try:
    con = sqlite3.connect(db); cur = con.cursor()
    for sym in ("BTC-USD","ETH-USD","SOL-USD","LINK-USD"):
        try:
            cur.execute("select count(*), min(ts), max(ts) from price where symbol=?", (sym,))
            print(sym, cur.fetchone())
        except Exception as e:
            print(sym, "ERROR:", e)
    con.close()
except Exception as e:
    print("OPEN ERROR:", e)

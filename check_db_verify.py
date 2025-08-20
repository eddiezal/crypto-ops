import sqlite3, os
db = r"F:\CryptoOps\crypto-ops\data\ledger.db"
con = sqlite3.connect(db); cur = con.cursor()
cols = [r[1] for r in cur.execute("PRAGMA table_info(price)").fetchall()]
print("price columns:", cols)
for sym in ("BTC-USD","ETH-USD","SOL-USD","LINK-USD"):
    try:
        cur.execute("select count(*), min(ts), max(ts) from price where symbol=?", (sym,))
        print(sym, cur.fetchone())
    except Exception as e:
        print(sym, "ERROR:", e)
con.close()

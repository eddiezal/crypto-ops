import sqlite3, os
db = r"F:\CryptoOps\crypto-ops\data\ledger.db"
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("PRAGMA journal_mode=WAL;")
cur.execute("PRAGMA busy_timeout=5000;")
cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uniq_price_symbol_ts ON price(symbol, ts)")
con.commit()
con.close()
print("WAL on, busy_timeout set, unique index ensured.")

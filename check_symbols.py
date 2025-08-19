import sqlite3
db = r"F:\CryptoOps\crypto-ops\data\ledger.db"
con = sqlite3.connect(db); cur = con.cursor()
cur.execute("SELECT symbol, COUNT(*) FROM price GROUP BY symbol ORDER BY COUNT(*) DESC LIMIT 10")
print(cur.fetchall())
con.close()

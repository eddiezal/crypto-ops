import sqlite3, sys, os

DB = os.path.join(os.path.dirname(__file__), "..", "data", "ledger.db")
DB = os.path.abspath(DB)

def colnames(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]

def main():
    if not os.path.exists(DB):
        print("DB not found:", DB); sys.exit(2)

    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price'")
    if not cur.fetchone():
        print("ERROR: table 'price' not found"); sys.exit(2)

    cols = [c.lower() for c in colnames(cur, "price")]
    print("price columns:", cols)

    if "symbol" not in cols:
        if "instrument_id" not in cols:
            print("ERROR: no symbol and no instrument_id; cannot proceed.")
            sys.exit(2)
        print("Adding symbol TEXT and populating from instrument_id ...")
        cur.execute("ALTER TABLE price ADD COLUMN symbol TEXT")
        cur.execute("UPDATE price SET symbol = instrument_id")
        con.commit()

    print("Creating index idx_price_symbol_ts if missing ...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_price_symbol_ts ON price(symbol, ts)")
    con.commit()

    for s in ("BTC-USD","ETH-USD","SOL-USD","LINK-USD"):
        try:
            cur.execute("SELECT COUNT(*), MIN(ts), MAX(ts) FROM price WHERE symbol=?", (s,))
            print(s, cur.fetchone())
        except Exception as e:
            print(s, "ERROR:", e)

    con.close()
    print("Done. DB patched.")

if __name__ == "__main__":
    main()

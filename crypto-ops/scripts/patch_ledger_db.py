import sqlite3, sys, os

DB = r"F:\CryptoOps\crypto-ops\data\ledger.db"

def colnames(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]

def pick_symbol_source(cols):
    lower = [c.lower() for c in cols]
    for cand in ("pair","product_id","instrument","ticker","symbol"):
        if cand in lower:
            return cols[lower.index(cand)]
    return None

def pick_price_source(cols):
    lower = [c.lower() for c in cols]
    for cand in ("px","price","close","last","mid"):
        if cand in lower:
            return cols[lower.index(cand)]
    return None

def main():
    if not os.path.exists(DB):
        print("DB not found:", DB)
        sys.exit(2)
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # Table present?
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price'")
    if not cur.fetchone():
        print("ERROR: table 'price' not found in DB")
        sys.exit(2)

    cols = colnames(cur, "price")
    print("price columns:", cols)

    # Ensure symbol column
    if "symbol" not in [c.lower() for c in cols]:
        sym_src = pick_symbol_source(cols)
        if not sym_src:
            print("ERROR: could not find a source column for symbol (looked for pair/product_id/instrument/ticker/symbol).")
            sys.exit(2)
        print(f"Adding symbol TEXT from {sym_src} ...")
        cur.execute("ALTER TABLE price ADD COLUMN symbol TEXT")
        cur.execute(f"UPDATE price SET symbol = {sym_src}")
        con.commit()
        cols = colnames(cur, "price")

    # Ensure px column
    if "px" not in [c.lower() for c in cols]:
        price_src = pick_price_source(cols)
        if not price_src:
            print("ERROR: could not find a price column (looked for px/price/close/last/mid).")
            sys.exit(2)
        if price_src.lower() == "px":
            print("px column already present.")
        else:
            print(f"Adding px REAL from {price_src} ...")
            cur.execute("ALTER TABLE price ADD COLUMN px REAL")
            cur.execute(f"UPDATE price SET px = {price_src}")
            con.commit()

    # Index for speed
    print("Creating index idx_price_symbol_ts if missing ...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_price_symbol_ts ON price(symbol, ts)")
    con.commit()

    # Quick sanity
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

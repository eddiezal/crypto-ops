import sqlite3, os, time, sys

DB = os.path.join(os.path.dirname(__file__), "..", "data", "ledger.db")
DB = os.path.abspath(DB)

def main():
    if not os.path.exists(DB):
        print("DB not found:", DB); sys.exit(2)

    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price'")
    if not cur.fetchone():
        print("ERROR: table 'price' not found"); sys.exit(2)

    cols = [r[1] for r in cur.execute("PRAGMA table_info(price)").fetchall()]
    lower = [c.lower() for c in cols]
    if "ts" not in lower:
        print("ERROR: column ts not found in price"); sys.exit(2)

    # Peek ts type
    cur.execute("SELECT typeof(ts) FROM price LIMIT 1")
    row = cur.fetchone()
    ts_type = row[0] if row else "unknown"
    print("Detected ts typeof():", ts_type)

    if ts_type == "integer":
        print("ts already integer epoch, nothing to do.")
        con.close(); return

    print("Rebuilding table with ts INTEGER (epoch seconds) ...")
    cur.execute("ALTER TABLE price RENAME TO price_old_{0}".format(int(time.time())))
    cur.execute("""
        CREATE TABLE price (
            ts INTEGER NOT NULL,
            instrument_id TEXT,
            symbol TEXT,
            px REAL,
            source TEXT
        )
    """)
    # Attempt to parse old ts (text) as epoch using strftime if needed:
    # Expect old ts as ISO8601 or epoch text; use unixepoch where possible.
    try:
        cur.execute("""
            INSERT INTO price (ts, instrument_id, symbol, px, source)
            SELECT
              CASE
                WHEN typeof(ts)='integer' THEN ts
                WHEN CAST(ts AS INTEGER) > 0 THEN CAST(ts AS INTEGER)
                ELSE CAST(strftime('%s', ts) AS INTEGER)
              END AS ts_epoch,
              instrument_id, symbol, px, source
            FROM price_old_{0}
        """.format(int(time.time())-1))
    except Exception:
        # simple fallback: try strftime only
        cur.execute("""
            INSERT INTO price (ts, instrument_id, symbol, px, source)
            SELECT CAST(strftime('%s', ts) AS INTEGER), instrument_id, symbol, px, source
            FROM (SELECT * FROM sqlite_temp_master) -- force fail if unknown
        """)
    con.commit()

    for s in ("BTC-USD","ETH-USD","SOL-USD","LINK-USD"):
        cur.execute("SELECT COUNT(*), MIN(ts), MAX(ts) FROM price WHERE symbol=?", (s,))
        print(s, cur.fetchone())

    print("Normalization complete.")
    con.close()

if __name__ == "__main__":
    main()

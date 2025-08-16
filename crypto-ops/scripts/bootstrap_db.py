from libs.db import apply_schema, get_conn, BASE_DIR
def seed():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO venue (id,kind) VALUES ('local','wallet')")
    cur.execute("INSERT OR IGNORE INTO account (id,venue_id,nickname) VALUES ('vault','local','Vault')")
    cur.execute("INSERT OR IGNORE INTO account (id,venue_id,nickname) VALUES ('trading','local','Trading')")
    cur.execute("INSERT OR IGNORE INTO instrument (id,symbol,kind) VALUES ('BTC-USD','BTC-USD','crypto')")
    cur.execute("INSERT OR IGNORE INTO instrument (id,symbol,kind) VALUES ('ETH-USD','ETH-USD','crypto')")
    cur.execute("INSERT OR IGNORE INTO instrument (id,symbol,kind) VALUES ('USD','USD','fiat')")
    conn.commit(); conn.close()
if __name__ == "__main__":
    import pathlib; (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    apply_schema(); seed(); print("SQLite ledger bootstrapped. Default venue/account/instruments seeded.")

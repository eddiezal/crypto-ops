from libs.db import get_conn

def latest_qty(conn, account, instr):
    r = conn.execute(
        "SELECT qty FROM balance_snapshot WHERE account_id=? AND instrument_id=? ORDER BY ts DESC LIMIT 1",
        (account, instr)
    ).fetchone()
    return r["qty"] if r else 0.0

def latest_price(conn, instr):
    r = conn.execute(
        "SELECT px FROM price WHERE instrument_id=? ORDER BY ts DESC LIMIT 1",
        (instr,)
    ).fetchone()
    return r["px"] if r else None

if __name__ == "__main__":
    acct = "trading"
    conn = get_conn()

    # discover instruments seen in snapshots (ex-USDT/USDC etc. by default we treat "-USD" as spot)
    syms = [row["instrument_id"] for row in conn.execute(
        "SELECT DISTINCT instrument_id FROM balance_snapshot WHERE account_id=?", (acct,)
    ) if row["instrument_id"] != "USD"]

    usd = latest_qty(conn, acct, "USD")
    rows = []
    total_crypto_val = 0.0
    for s in syms:
        q = latest_qty(conn, acct, s)
        p = latest_price(conn, s) or 0.0
        val = q * p
        total_crypto_val += val
        rows.append((s, q, p, val))

    nav = usd + total_crypto_val
    rows.sort(key=lambda x: x[3], reverse=True)

    print("=== Latest Balances (trading) ===")
    print(f"USD: ${usd:,.2f}")
    for s,q,p,val in rows:
        print(f"{s}: {q:.6f} (~${val:,.2f}) @ ${p:,.2f}")

    if total_crypto_val > 0:
        print("Crypto Weights ->", end=" ")
        parts = []
        for s,q,p,val in rows:
            w = val/total_crypto_val
            parts.append(f"{s[:-4]}: {w:.2%}")
        print(", ".join(parts))

    print(f"NAV (USD): ${nav:,.2f}")

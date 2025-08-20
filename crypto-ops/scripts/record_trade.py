import argparse, datetime, uuid
from libs.db import get_conn

def now_ts():
    # microsecond precision, UTC
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

def latest_price(conn, instr):
    r = conn.execute("SELECT px FROM price WHERE instrument_id=? ORDER BY ts DESC LIMIT 1", (instr,)).fetchone()
    return r["px"] if r else None

def latest_qty(conn, account, instr):
    r = conn.execute("SELECT qty FROM balance_snapshot WHERE account_id=? AND instrument_id=? ORDER BY ts DESC LIMIT 1", (account, instr)).fetchone()
    return r["qty"] if r else 0.0

def write_snapshot(conn, account, usd, spot_qtys: dict):
    ts = now_ts()
    cur = conn.cursor()
    # USD first (UPSERT)
    cur.execute("""
        INSERT INTO balance_snapshot(ts,account_id,instrument_id,qty)
        VALUES(?,?,?,?)
        ON CONFLICT(ts,account_id,instrument_id) DO UPDATE SET qty=excluded.qty
    """,(ts,account,"USD",usd))
    # then all symbols (UPSERT)
    for sym, q in spot_qtys.items():
        cur.execute("""
            INSERT INTO balance_snapshot(ts,account_id,instrument_id,qty)
            VALUES(?,?,?,?)
            ON CONFLICT(ts,account_id,instrument_id) DO UPDATE SET qty=excluded.qty
        """,(ts,account,sym,q))
    conn.commit()

def fee_to_usd(fee_qty, fee_asset, px_map):
    a = (fee_asset or "USD").upper()
    if fee_qty is None: return 0.0
    if a == "USD": return float(fee_qty)
    if a == "BTC": return float(fee_qty) * (px_map.get("BTC-USD") or 0.0)
    if a == "ETH": return float(fee_qty) * (px_map.get("ETH-USD") or 0.0)
    return 0.0

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--account","-a", default="trading")
    p.add_argument("--symbol", required=True, help="e.g., BTC-USD, ETH-USD, SOL-USD, LINK-USD")
    p.add_argument("--side", required=True, choices=["buy","sell"])
    p.add_argument("--qty", type=float, required=True)
    p.add_argument("--px",  type=float, required=True)
    p.add_argument("--fee", type=float, default=0.0)
    p.add_argument("--fee-asset", default="USD", help="USD, BTC, or ETH")
    args = p.parse_args()

    conn = get_conn(); cur = conn.cursor()

    # Ensure instrument exists
    kind = "fiat" if args.symbol.upper()=="USD" else "crypto"
    cur.execute("INSERT OR IGNORE INTO instrument(id,symbol,kind) VALUES(?,?,?)",(args.symbol, args.symbol, kind))

    # Prices & current balances
    px_map = {
        "BTC-USD": latest_price(conn, "BTC-USD"),
        "ETH-USD": latest_price(conn, "ETH-USD"),
        args.symbol: args.px
    }
    usd = latest_qty(conn, args.account, "USD")
    spot_qty = latest_qty(conn, args.account, args.symbol)

    # Record order/trade
    ts = now_ts()
    order_id = "ord_"+uuid.uuid4().hex
    trade_id = "tr_"+uuid.uuid4().hex
    cur.execute("INSERT INTO 'order'(id,ts,account_id,instrument_id,side,ord_type,qty,px,status) VALUES(?,?,?,?,?,?,?,?,?)",
                (order_id, ts, args.account, args.symbol, args.side, "market", args.qty, args.px, "filled"))
    fee_instr = "USD" if args.fee_asset.upper()=="USD" else ("BTC-USD" if args.fee_asset.upper()=="BTC" else "ETH-USD")
    cur.execute("INSERT INTO trade(id,ts,order_id,account_id,instrument_id,side,qty,px,fee_qty,fee_instrument_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (trade_id, ts, order_id, args.account, args.symbol, args.side, args.qty, args.px, args.fee, fee_instr))

    # Fees in USD
    fee_usd = fee_to_usd(args.fee, args.fee_asset, px_map)

    # LOT + balances
    realized = 0.0
    if args.side == "buy":
        open_qty = args.qty
        if args.fee_asset.upper() in ("BTC","ETH") and ((args.symbol=="BTC-USD" and args.fee_asset.upper()=="BTC") or (args.symbol=="ETH-USD" and args.fee_asset.upper()=="ETH")):
            open_qty = max(0.0, args.qty - args.fee)
        open_px_eff = (args.px*args.qty + fee_usd) / args.qty if args.qty>0 else args.px
        lot_id = "lot_"+uuid.uuid4().hex
        cur.execute("INSERT INTO lot(id,open_ts,account_id,instrument_id,open_qty,open_px,remaining_qty) VALUES(?,?,?,?,?,?,?)",
                    (lot_id, ts, args.account, args.symbol, open_qty, open_px_eff, open_qty))
        usd -= args.qty*args.px
        spot_qty += args.qty
    else:
        # HIFO sell
        sell_qty = args.qty
        alloc_fee_per_unit = (fee_usd / sell_qty) if sell_qty>0 else 0.0
        lots = list(cur.execute("""SELECT id, remaining_qty, open_px 
                                   FROM lot 
                                   WHERE account_id=? AND instrument_id=? AND remaining_qty>0 
                                   ORDER BY open_px DESC""",(args.account, args.symbol)))
        remaining = sell_qty
        if not lots:
            raise SystemExit("No open lots to match this sale. Seed lots first.")
        for (lot_id, rem_qty, open_px) in lots:
            if remaining <= 0: break
            take = min(remaining, rem_qty)
            proceeds = (args.px - alloc_fee_per_unit) * take
            cost = open_px * take
            gl = proceeds - cost
            cur.execute("INSERT INTO lot_event(id,ts,lot_id,trade_id,qty,proceeds,gain_loss) VALUES(?,?,?,?,?,?,?)",
                        ("le_"+uuid.uuid4().hex, ts, lot_id, trade_id, take, proceeds, gl))
            cur.execute("UPDATE lot SET remaining_qty = remaining_qty - ? WHERE id=?", (take, lot_id))
            realized += gl
            remaining -= take
        if remaining > 1e-9:
            raise SystemExit("Not enough lot quantity to match this sale.")
        usd += args.qty*args.px
        spot_qty -= args.qty

    # Apply fee to balances
    if args.fee_asset.upper() == "USD":
        usd -= args.fee
    elif args.fee_asset.upper() == "BTC" and args.symbol=="BTC-USD":
        spot_qty -= args.fee
    elif args.fee_asset.upper() == "ETH" and args.symbol=="ETH-USD":
        spot_qty -= args.fee

    conn.commit()
    write_snapshot(conn, args.account, usd, {args.symbol: spot_qty})

    print(f"Recorded trade {args.side.upper()} {args.qty} {args.symbol} @ ${args.px} fee {args.fee} {args.fee_asset}.")
    if args.side == "sell":
        print(f"Realized PnL (USD): {realized:.2f}")
    print(f"New {args.account} balances -> USD: {usd:.2f}, {args.symbol}: {spot_qty:.6f}")

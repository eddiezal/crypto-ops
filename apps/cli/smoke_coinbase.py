import os, json, sys
from apps.exchange.coinbase_client import get_accounts, get_best_bid_ask, preview_buy

def main():
    print("== Coinbase Advanced Smoke ==")
    # 1) Accounts
    accts = get_accounts()
    print(f"Accounts: {len(accts)}")
    if accts:
        # show first 2 account symbols + balances
        for a in accts[:2]:
            print(" -", a.get("currency"), a.get("available_balance",{}).get("value"))

    # 2) Best bid/ask
    t = get_best_bid_ask(["BTC-USD","ETH-USD"])
    print("BestBidAsk:", json.dumps(t)[:300], "...")

    # 3) Safe DRY-RUN: preview a tiny buy
    pv = preview_buy("BTC-USD", quote_size="5")
    print("Preview BUY $5 BTC → OK" if pv else "Preview failed")
    print("DONE")

if __name__ == "__main__":
    main()

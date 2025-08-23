import os, sys
from apps.exchange.coinbase_client import place_tiny_buy

DRY_RUN = os.getenv("DRY_RUN","1")  # default: DRY_RUN
if DRY_RUN != "0":
    print("DRY_RUN=1 → exiting without placing order")
    sys.exit(0)

resp = place_tiny_buy("BTC-USD", quote_size="2")   # $2 notional
print("Order response:", resp)

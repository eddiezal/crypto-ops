import os, json, time
from pathlib import Path

# You can swap this for coinbase-advanced-py later; this stub simulates success
def get_sandbox_accounts():
    # TODO: replace with real API call
    return {"USD": 2683.022850014763, "BTC": 1.703531964692791, "ETH": 19.972825658393063}

def main():
    acct = get_sandbox_accounts()
    out = {
        "ts": int(time.time()),
        "source": "coinbase_sandbox",
        "balances": acct
    }
    Path("logs").mkdir(parents=True, exist_ok=True)
    Path("logs/recon").mkdir(parents=True, exist_ok=True)
    with open("logs/recon/coinbase_sandbox.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(out) + "\n")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()

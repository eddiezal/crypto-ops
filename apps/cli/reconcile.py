import json, os, sys
from apps.exchange.coinbase_client import get_accounts

# Load GCS state via your existing code path (your /plan already reads these)
# Here we read from local file to keep it simple; in service, reuse state.read_json
STATE_PATH = os.getenv("STATE_PATH", "state/balances.json")

def to_float(v):
    try:
        return float(v)
    except:
        return 0.0

def load_local_state(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"USD":0.0,"BTC":0.0,"ETH":0.0}

def balances_from_coinbase():
    accs = get_accounts()
    out = {"USD":0.0,"BTC":0.0,"ETH":0.0}
    for a in accs:
        cur = a.get("currency")
        val = to_float(a.get("available_balance",{}).get("value"))
        if cur in out:
            out[cur] = val
    return out

def main():
    cb = balances_from_coinbase()
    st = load_local_state(STATE_PATH)
    print("Coinbase:", cb)
    print("State   :", st)

    # Simple delta report
    for k in ["USD","BTC","ETH"]:
        dv = cb.get(k,0)-st.get(k,0)
        if abs(dv) > 1e-8:
            print(f"Δ {k}: {dv:+.8f}")

if __name__ == "__main__":
    main()

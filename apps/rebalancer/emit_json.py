import sys, json, argparse
from apps.rebalancer.main import compute_actions
from apps.infra.versioning import version_info

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", action="append", help="(what-if) SYMBOL=price; repeatable")
    args = ap.parse_args()

    overrides = {}
    for kv in (args.pair or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            overrides[k.strip()] = float(v)

    plan = compute_actions("trading", override_prices=overrides or None)
    if isinstance(plan, dict):
        plan.setdefault("version", version_info())
    print(json.dumps(plan, indent=2))

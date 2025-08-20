import json, datetime
from pathlib import Path
from apps.rebalancer.main import compute_actions
BASE = Path(__file__).resolve().parents[2]
PLANS = BASE / "plans"
PLANS.mkdir(parents=True, exist_ok=True)
plan = compute_actions("trading")
ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
out = PLANS / f"plan_{ts}.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(plan, f, indent=2)
print(f"Plan written: {out}")
if plan.get("actions"):
    print("Actions:", len(plan["actions"]), "Total $:", round(sum(abs(a["usd"]) for a in plan["actions"]),2))
else:
    print("No actions.")

# apps/rebalancer/emit_plan.py
import sys, json, time
from pathlib import Path

# Import the planner
from apps.rebalancer.main import compute_actions

BASE = Path(__file__).resolve().parents[2]
PLANS_DIR = BASE / "plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)

def write_plan(plan: dict) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    out = PLANS_DIR / f"plan_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    return out

if __name__ == "__main__":
    plan = compute_actions("trading")

    # If the planner ever returns an error, echo and exit non‑zero
    if not isinstance(plan, dict):
        print("Planner returned unexpected result; aborting.")
        sys.exit(2)
    if "error" in plan:
        print(f"Planner error: {plan['error']}")
        # Still write it so you can inspect what happened
        out = write_plan(plan)
        print(f"Plan written (with error): {out}")
        sys.exit(3)

    out = write_plan(plan)
    print(f"Plan written: {out}")

    actions = plan.get("actions", []) or []
    if actions:
        total_usd = sum(abs(a.get("usd", 0.0)) for a in actions)
        print(f"Actions: {len(actions)} Total $: {total_usd:,.2f}")
    else:
        print("No actions.")

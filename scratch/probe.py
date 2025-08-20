from apps.rebalancer.main import compute_actions
from pprint import pprint

p = compute_actions("trading")
print("TYPE:", type(p).__name__)
if isinstance(p, dict):
    print("keys:", sorted(list(p.keys()))[:8])
    print("n_actions:", len(p.get("actions", [])))
    print("config.band:", p.get("config",{}).get("band"))
    print("\nactions:")
    pprint(p.get("actions"))
else:
    print("Unexpected planner return:", p)

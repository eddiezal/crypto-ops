from apps.rebalancer.main import compute_actions
p = compute_actions("trading")
print("TYPE:", type(p).__name__)
if isinstance(p, dict) and "error" in p:
    print("ERROR:", p["error"])
else:
    print("OK, actions:", len(p.get("actions", [])) if isinstance(p, dict) else None)

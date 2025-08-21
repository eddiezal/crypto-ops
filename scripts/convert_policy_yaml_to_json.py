import json, yaml
from pathlib import Path

base = Path(__file__).resolve().parents[1]
src = base / "configs" / "policy.rebalancer.yaml"
dst = base / "configs" / "policy.rebalancer.json"

data = yaml.safe_load(src.read_text(encoding="utf-8"))
dst.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Wrote {dst}")

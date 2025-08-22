from __future__ import annotations
from pathlib import Path
import json

# Resolve repo root: .../apps/infra/state_local.py -> parents[2] is the repo root
_ROOT = Path(__file__).resolve().parents[2]

def _p(rel: str) -> Path:
    # Normalize and map "state/..." etc to a file under repo root
    return (_ROOT / rel).resolve()

def read_text(path: str, default: str | None = None) -> str | None:
    try:
        return _p(path).read_text(encoding="utf-8")
    except Exception:
        return default

def write_text(path: str, data: str) -> None:
    p = _p(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data, encoding="utf-8")

def read_json(path: str, default=None):
    try:
        t = read_text(path, default=None)
        if t is None or t == "":
            return default
        return json.loads(t)
    except Exception:
        return default

def write_json(path: str, obj) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False))

def append_jsonl(path: str, obj) -> None:
    p = _p(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

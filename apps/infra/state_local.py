from __future__ import annotations
from pathlib import Path
import json
from typing import Any, Dict, List, Optional

# Resolve repo root: .../apps/infra/state_local.py -> parents[2] is repo
_REPO = Path(__file__).resolve().parents[2]

def _to_abs(path: str) -> Path:
    p = Path(path)
    # If caller passes a relative path like "state/foo.json", resolve under repo root
    return (_REPO / p) if not p.is_absolute() else p

def read_text(path: str, default: Optional[str] = None) -> Optional[str]:
    fp = _to_abs(path)
    try:
        return fp.read_text(encoding="utf-8")
    except Exception:
        return default

def write_text(path: str, text: str) -> None:
    fp = _to_abs(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(text, encoding="utf-8")

def read_json(path: str, default: Any = None) -> Any:
    fp = _to_abs(path)
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path: str, obj: Any) -> None:
    fp = _to_abs(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def append_jsonl(path: str, obj: Any) -> None:
    fp = _to_abs(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def read_ndjson(path: str, default: Any = None) -> Any:
    """
    Minimal NDJSON reader for local mode. Returns list of JSON objects.
    """
    fp = _to_abs(path)
    rows: List[Any] = []
    try:
        with fp.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    # Skip malformed lines
                    pass
        return rows
    except Exception:
        return default

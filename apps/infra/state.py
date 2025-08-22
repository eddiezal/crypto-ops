from __future__ import annotations
import os, json
from pathlib import Path
from typing import Any, Dict, Optional, Iterable

# Default: LOCAL filesystem under repo root (two levels up from this file)
_ROOT = Path(__file__).resolve().parents[2]

def _p(rel: str) -> Path:
    p = (_ROOT / rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def read_text(rel: str, default: Optional[str] = None) -> Optional[str]:
    try:
        return _p(rel).read_text(encoding="utf-8")
    except Exception:
        return default

def write_text(rel: str, data: str) -> None:
    _p(rel).write_text(data, encoding="utf-8")

def read_json(rel: str, default: Optional[Any] = None) -> Any:
    try:
        t = read_text(rel, None)
        if t is None: return default
        return json.loads(t)
    except Exception:
        return default

def write_json(rel: str, obj: Any) -> None:
    write_text(rel, json.dumps(obj, ensure_ascii=False, indent=2))

def read_ndjson(rel: str) -> Iterable[Dict[str, Any]]:
    t = read_text(rel, None)
    if t is None: return []
    for line in t.splitlines():
        line = line.strip()
        if not line: continue
        try:
            yield json.loads(line)
        except Exception:
            continue

def append_jsonl(rel: str, obj: Dict[str, Any]) -> None:
    p = _p(rel)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":")) + "\n")

# Optional GCS override if STATE_BUCKET is set
_BUCKET = os.getenv("STATE_BUCKET")
if _BUCKET:
    try:
        from . import state_gcs as _g
        # Prefer GCS implementations when bucket is defined
        read_text    = _g.read_text
        write_text   = _g.write_text
        read_json    = _g.read_json
        write_json   = _g.write_json
        read_ndjson  = _g.read_ndjson
        append_jsonl = _g.append_jsonl
    except Exception:
        # If GCS layer fails to import or operate, keep local fallback
        pass

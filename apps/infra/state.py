from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict

"""
Universal state shim.

- Local filesystem (default): no envs needed.
- Google Cloud Storage: enabled ONLY if STATE_BUCKET env var is non-empty.
  Requires apps/infra/state_gcs.py in the image and Cloud Run SA IAM.
"""

def _use_gcs() -> bool:
    return bool(os.getenv("STATE_BUCKET", "").strip())

# ---------- Local FS implementations ----------
def _fs_path(p: str) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = Path.cwd() / p
    return path

def _fs_read_text(path: str) -> str:
    p = _fs_path(path)
    return p.read_text(encoding="utf-8")

def _fs_write_text(path: str, data: str) -> None:
    p = _fs_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data, encoding="utf-8")

def _fs_read_json(path: str, default: Any = None) -> Any:
    try:
        t = _fs_read_text(path)
        return json.loads(t) if t and t.strip() else (default if default is not None else None)
    except Exception:
        return default

def _fs_write_json(path: str, obj: Any) -> None:
    _fs_write_text(path, json.dumps(obj, ensure_ascii=False))

def _fs_append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    p = _fs_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# ---------- Public API ----------
def read_text(path: str) -> str:
    if _use_gcs():
        from . import state_gcs as gcs
        return gcs.read_text(path)
    return _fs_read_text(path)

def write_text(path: str, data: str) -> None:
    if _use_gcs():
        from . import state_gcs as gcs
        gcs.write_text(path, data); return
    _fs_write_text(path, data)

def read_json(path: str, default: Any = None) -> Any:
    if _use_gcs():
        from . import state_gcs as gcs
        return gcs.read_json(path, default=default)
    return _fs_read_json(path, default=default)

def write_json(path: str, obj: Any) -> None:
    if _use_gcs():
        from . import state_gcs as gcs
        gcs.write_json(path, obj); return
    _fs_write_json(path, obj)

def append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    if _use_gcs():
        from . import state_gcs as gcs
        gcs.append_jsonl(path, obj); return
    _fs_append_jsonl(path, obj)

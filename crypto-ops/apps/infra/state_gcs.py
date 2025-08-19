import os, json
from typing import List, Dict, Any, Optional
from google.cloud import storage
from google.api_core.exceptions import NotFound

_BUCKET  = os.getenv("STATE_BUCKET")
_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")

def _client():
    return storage.Client(project=_PROJECT) if _PROJECT else storage.Client()

def _bucket():
    if not _BUCKET:
        raise RuntimeError("STATE_BUCKET env var not set")
    return _client().bucket(_BUCKET)

def read_text(path: str) -> Optional[str]:
    b = _bucket()
    blob = b.blob(path)
    try:
        return blob.download_as_text()
    except NotFound:
        return None

def read_json(path: str, default=None):
    t = read_text(path)
    if t is None:
        return default
    try:
        return json.loads(t)
    except Exception:
        return default

def read_ndjson(path: str) -> List[Dict[str, Any]]:
    """Return list of dicts from NDJSON (one JSON object per line)."""
    txt = read_text(path)
    if not txt:
        return []
    out: List[Dict[str, Any]] = []
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            pass
    return out

def write_text(path: str, text: str, content_type: str = "application/json"):
    b = _bucket()
    blob = b.blob(path)
    blob.cache_control = "no-store"
    # IMPORTANT: pass content_type here so HTTP header == metadata Content-Type
    blob.upload_from_string(text, content_type=content_type)

def write_json(path: str, obj: Any):
    write_text(path, json.dumps(obj, separators=(",",":")), content_type="application/json")

def append_jsonl(path: str, obj: Dict[str, Any]):
    """Append a JSON line; set a clear content-type for NDJSON."""
    line = json.dumps(obj, separators=(",",":")) + "\n"
    cur = read_text(path)
    payload = line if cur is None else (cur + line)
    write_text(path, payload, content_type="application/x-ndjson")

def selftest(prefix="state"):
    b = _bucket()
    p = f"{prefix}/selftest.txt"
    try:
        blob = b.blob(p)
        blob.upload_from_string("ok", content_type="text/plain")
        t = blob.download_as_text()
        blob.delete()
        return True, f"wrote/read/deleted gs://{_BUCKET}/{p} -> '{t}'"
    except Exception as e:
        return False, f"{e.__class__.__name__}: {e}"

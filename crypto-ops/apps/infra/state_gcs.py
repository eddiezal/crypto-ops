import os, json
from google.cloud import storage
from google.api_core.exceptions import NotFound

_BUCKET = os.getenv("STATE_BUCKET")
_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")

def _client():
    return storage.Client(project=_PROJECT) if _PROJECT else storage.Client()

def _bucket():
    if not _BUCKET:
        raise RuntimeError("STATE_BUCKET env var not set")
    return _client().bucket(_BUCKET)

def read_text(path: str):
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

def write_text(path: str, text: str, content_type="application/json"):
    b = _bucket()
    blob = b.blob(path)
    # Important: pass content_type into upload_from_string to align header+metadata
    blob.cache_control = "no-store"
    blob.upload_from_string(text, content_type=content_type)

def write_json(path: str, obj):
    write_text(path, json.dumps(obj, separators=(",",":")), content_type="application/json")

def append_jsonl(path: str, obj):
    # JSON Lines; use a clear type to avoid ambiguity
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

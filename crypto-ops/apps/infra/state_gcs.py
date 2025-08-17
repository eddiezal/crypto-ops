# apps/infra/state_gcs.py
import os, json
from google.cloud import storage
from google.api_core.exceptions import NotFound

_BUCKET = os.getenv("STATE_BUCKET")

def _client():
    return storage.Client()

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
    blob.cache_control = "no-store"
    blob.content_type = content_type
    blob.upload_from_string(text)

def write_json(path: str, obj):
    write_text(path, json.dumps(obj, separators=(",",":")))

def append_jsonl(path: str, obj):
    line = json.dumps(obj, separators=(",",":")) + "\n"
    cur = read_text(path)
    if cur is None:
        write_text(path, line, content_type="text/plain")
    else:
        write_text(path, cur + line, content_type="text/plain")

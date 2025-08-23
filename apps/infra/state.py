"""State management with explicit backend selection and safe fallback."""
import json, os
from pathlib import Path
from typing import Any, Optional, Union

# --- Local file helpers ---
def _read_json_local(filepath: Union[str, Path], default: Optional[Any] = None) -> Any:
    try:
        p = Path(filepath)
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: local read failed for {filepath}: {e}")
    return default

def _write_json_local(filepath: Union[str, Path], data: Any) -> None:
    try:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: local write failed for {filepath}: {e}")

def _append_jsonl_local(filepath: Union[str, Path], data: Any) -> None:
    try:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data) + '\n')
    except Exception as e:
        print(f"Warning: local append failed for {filepath}: {e}")

# --- Optional GCS helpers (imported lazily so local dev doesn't require the lib) ---
def _read_json_gcs(object_path: str, default: Optional[Any] = None) -> Any:
    try:
        from google.cloud import storage
        if object_path.startswith("gs://"):
            _, _, bucket, *obj = object_path.split("/", 3)
            object_name = obj[-1] if obj else ""
        else:
            bucket = os.environ["STATE_BUCKET"]
            object_name = object_path
        client = storage.Client()
        blob = client.bucket(bucket).blob(object_name)
        if not blob.exists():
            return default
        return json.loads(blob.download_as_text())
    except Exception as e:
        print(f"Warning: gcs read failed for {object_path}: {e}")
        return default

def _write_json_gcs(object_path: str, data: Any) -> None:
    try:
        from google.cloud import storage
        if object_path.startswith("gs://"):
            _, _, bucket, *obj = object_path.split("/", 3)
            object_name = obj[-1] if obj else ""
        else:
            bucket = os.environ["STATE_BUCKET"]
            object_name = object_path
        client = storage.Client()
        client.bucket(bucket).blob(object_name).upload_from_string(json.dumps(data))
    except Exception as e:
        print(f"Warning: gcs write failed for {object_path}: {e}")

def _append_jsonl_gcs(object_path: str, data: Any) -> None:
    # Simple append-by-read+write (fine for low volume; replace with compose if needed)
    try:
        existing = _read_json_gcs(object_path, default=None)
        # If not JSONL compatible, fall back to creating a new line
        line = json.dumps(data) + "\n"
        if existing is None:
            _write_json_gcs(object_path, line)
        else:
            from google.cloud import storage
            if object_path.startswith("gs://"):
                _, _, bucket, *obj = object_path.split("/", 3)
                object_name = obj[-1] if obj else ""
            else:
                bucket = os.environ["STATE_BUCKET"]
                object_name = object_path
            client = storage.Client()
            blob = client.bucket(bucket).blob(object_name)
            content = blob.download_as_text() + line
            blob.upload_from_string(content)
    except Exception as e:
        print(f"Warning: gcs append failed for {object_path}: {e}")

# --- Backend selection ---
BACKEND = os.getenv("STATE_BACKEND", "local")   # 'local' | 'gcs' | 'auto'
BUCKET  = os.getenv("STATE_BUCKET", "")

def _want_gcs(path: Union[str, Path]) -> bool:
    if BACKEND == "gcs":
        return True
    if BACKEND == "local":
        return False
    # 'auto': prefer GCS only if bucket is defined AND local file is absent
    return bool(BUCKET) and (not Path(str(path)).exists())

def read_json(path: Union[str, Path], default: Optional[Any] = None) -> Any:
    if _want_gcs(path):
        obj = f"state/{Path(path).name}" if not str(path).startswith("gs://") else str(path)
        return _read_json_gcs(obj, default)
    return _read_json_local(path, default)

def write_json(path: Union[str, Path], data: Any) -> None:
    if _want_gcs(path):
        obj = f"state/{Path(path).name}" if not str(path).startswith("gs://") else str(path)
        return _write_json_gcs(obj, data)
    return _write_json_local(path, data)

def append_jsonl(path: Union[str, Path], data: Any) -> None:
    if _want_gcs(path):
        obj = f"logs/{Path(path).name}" if not str(path).startswith("gs://") else str(path)
        return _append_jsonl_gcs(obj, data)
    return _append_jsonl_local(path, data)

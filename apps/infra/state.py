"""State management with fallback to local files or memory"""
import json
import os
from pathlib import Path
from typing import Any, Optional, Union

def read_json(filepath: Union[str, Path], default: Optional[Any] = None) -> Any:
    """Read JSON file, return default if not found"""
    try:
        path = Path(filepath) if isinstance(filepath, str) else filepath
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}")
    return default

def write_json(filepath: Union[str, Path], data: Any) -> None:
    """Write data to JSON file"""
    try:
        path = Path(filepath) if isinstance(filepath, str) else filepath
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not write {filepath}: {e}")

def append_jsonl(filepath: Union[str, Path], data: Any) -> None:
    """Append data as JSON line"""
    try:
        path = Path(filepath) if isinstance(filepath, str) else filepath
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data) + '\n')
    except Exception as e:
        print(f"Warning: Could not append to {filepath}: {e}")

# Try to import GCS versions if available (but don't fail if not)
try:
    from .state_gcs import *  # noqa
except ImportError:
    pass  # Use local file versions above

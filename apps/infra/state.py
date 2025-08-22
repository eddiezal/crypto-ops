# apps/infra/state.py — safe conditional shim
import os

def _use_gcs() -> bool:
    v = (os.getenv("STATE_BUCKET") or "").strip()
    return bool(v)

try:
    if _use_gcs():
        from .state_gcs import (  # type: ignore
            read_text, read_json, read_ndjson,
            write_text, write_json, append_jsonl
        )
    else:
        from .state_local import (  # type: ignore
            read_text, read_json, read_ndjson,
            write_text, write_json, append_jsonl
        )
except Exception:
    # Belt & suspenders: never crash imports — fall back to local
    from .state_local import (  # type: ignore
        read_text, read_json, read_ndjson,
        write_text, write_json, append_jsonl
    )

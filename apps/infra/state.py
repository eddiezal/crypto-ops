from __future__ import annotations
import os

# Auto-select backend: local if STATE_BUCKET is not set, GCS if it is
if os.getenv("STATE_BUCKET"):
    from .state_gcs import (
        read_text, write_text,
        read_json, write_json,
        append_jsonl,
    )
else:
    from .state_local import (
        read_text, write_text,
        read_json, write_json,
        append_jsonl,
    )

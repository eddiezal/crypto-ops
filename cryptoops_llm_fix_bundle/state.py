# Compatibility shim — allow imports via `apps.infra.state` or `apps.infra.state_gcs`
from .state_gcs import (
    read_text,
    read_json,
    read_ndjson,
    write_text,
    write_json,
    append_jsonl,
)

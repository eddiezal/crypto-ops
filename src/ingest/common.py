from __future__ import annotations

import os
import pandas as pd  # type: ignore[import-not-found]

RATE_LIMIT_PER_SEC = float(os.getenv("INGEST_RPS", "5"))

def bq_write_v3(df: pd.DataFrame, table: str = "crypto.price", if_exists: str = "append") -> None:
    """Write DataFrame to BigQuery (schema v3).
    DRY_RUN=1 will log instead of writing. Set GCP_PROJECT/BQCRED_PATH appropriately.
    """  # noqa: D401
    if os.getenv("DRY_RUN", "1") != "0":
        print(f"[DRY_RUN] bq_write_v3 -> {table} rows={len(df)}")
        return
    from google.cloud import bigquery  # type: ignore[import-not-found]
    client = bigquery.Client(project=os.getenv("GCP_PROJECT"))
    job = client.load_table_from_dataframe(df, table)
    job.result()
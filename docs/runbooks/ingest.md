# Runbook: Ingest

- **Backfill**: `python -c "from src.ingest.ingest_binance import backfill; import pandas as pd; df=backfill('BTC/USDT',30); print(df.head())"`
- **Write**: `DRY_RUN=0` to enable BigQuery writes via `bq_write_v3(df)`.
- **Rate limit**: env `INGEST_RPS` (default 5).
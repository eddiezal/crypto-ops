SELECT
  TIMESTAMP_SECONDS(CAST(ts AS INT64)) AS ts_utc,
  symbol, side, usd, qty, run_id
FROM cryptoops.trades_gcs
ORDER BY ts DESC
LIMIT 20

SELECT
  TIMESTAMP_SECONDS(CAST(ts AS INT64)) AS ts_utc,
  nav, nav_before, actions_count, source, revision
FROM cryptoops.snapshots_daily
ORDER BY ts DESC
LIMIT 50

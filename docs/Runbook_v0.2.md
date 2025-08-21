# Runbook v0.2 — Paper Cycle MVP

## Config (defaults)
pairs=["BTC-USD","ETH-USD"]; DAILY_TURNOVER_CAP_PCT=90; PAIR_MAX_EXPOSURE_PCT=60;
MAX_SLIPPAGE_PCT=30; FEE_BPS=10; LEDGER_PATH=./data/ledger/; LOG_PATH=./data/logs/; MODE=paper

## Env
TRADING_MODE=paper; COINBASE_ENV=sandbox; APP_KEY=(required for /snapshot_now);
STATE_BUCKET=(GCS); optional: LEDGER_DB(_GCS) (not required for MVP loop)

## Operational Steps
1. Init: ULID cycle_id; assert paper/sandbox; load config/env.
2. Inputs: balances from state/balances.json (numeric only); prices from last snapshot or public feed.
3. Targets: compute deltas; propose orders.
4. Constraints: enforce turnover/exposure/slippage/fees; log ConstraintHit if trimmed/denied.
5. Outputs:
   - JSON logs: LOG_PATH/cycle_<id>.jsonl (events: CycleStart/ActionProposed/ConstraintHit/ActionFinal/LedgerWrite/CycleEnd/Error)
   - Ledger: LEDGER_PATH/… (idempotent on cycle_id)
   - Summary: LOG_PATH/cycle_<id>.txt
6. Analytics: /snapshot_now (APP_KEY) computes NAV, appends to snapshots/daily.jsonl; Scheduler hourly.
7. Kill switch: env KILL=1 or ./kill.flag ⇒ immediate safe halt; partial snapshot; non-zero exit.

## Cloud Run
- Tripwires at startup; never 500 on missing DB; fallbacks with banner.
- Health: /_ah/health returns paper/sandbox + revision.
- Band policy read from configs/policy.rebalancer.{json,yaml}; both /plan and /plan_band must publish same band.

## Recovery
Re-run safe (idempotency). If Scheduler 404s, delete bad jobs or implement routes. If band mismatch, fix /plan success path.

## Log schema (minimum)
{ ts, level, cycle_id, event, pair?, action?, qty?, px?, fee_bps?, fee?, slippage_pct?, reason?, constraints? }

# PRD v0.2 — Paper Cycle MVP (Cloud + Local)

## Problem
We need a boring, auditable paper-trading loop for BTC-USD and ETH-USD that enforces risk constraints, logs deterministically, exposes health/plan APIs, and produces basic analytics. Must run locally and in Cloud Run (paper/sandbox only).

## Users
1) Operator: runs cycles, reviews reports/alerts, raises kill switch.
2) Auditor: inspects JSON logs, ledger, and analytics snapshots.

## Scope (MVP)
- Deterministic **paper_cycle** for ["BTC-USD","ETH-USD"].
- Hard constraints: DAILY_TURNOVER_CAP_PCT, PAIR_MAX_EXPOSURE_PCT, MAX_SLIPPAGE_PCT, FEE_BPS.
- Structured JSON logs + human summary.
- Idempotent ledger writer (cycle_id).
- Cloud Run API: /_ah/health, /plan, /plan_band, /snapshot_now (APP_KEY), (optional) /dashboard (read-only minimal UI).
- Analytics: /snapshot_now (NAV), JSONL at snapshots/, hourly Scheduler job to record NAV.
- Safety: startup tripwires (paper/sandbox), APP_KEY on mutating/analytics, fallback paths never 500.

## Non-goals
Live trading, multi-exchange, advanced order types, fancy UI.

## Flow
Load config/env → assert tripwires → load balances/prices → compute targets → propose orders → enforce constraints (turnover/exposure/slippage/fees) → finalize actions → write JSON logs + ledger (idempotent) → emit summary → exit code.

## Constraints (defaults)
DAILY_TURNOVER_CAP_PCT=90, PAIR_MAX_EXPOSURE_PCT=60, MAX_SLIPPAGE_PCT=30, FEE_BPS=10.

## Risks
Bad numeric inputs; env drift; scheduler pointing at missing routes; inconsistent config (band); duplicate ledger writes.

## Acceptance Criteria (AC)
AC1 Idempotency: same inputs ⇒ same ledger/logs.
AC2 Constraints enforced; violations logged as ConstraintHit.
AC3 Kill switch halts safely, writes partial snapshot, non-zero exit.
AC4 Logs include: ts, cycle_id, pair, action, qty, px, fee, slippage, reason, constraints.
AC5 Cloud Run health shows paper/sandbox; **/plan and /plan_band publish policy band** (from policy.rebalancer).
AC6 /snapshot_now requires APP_KEY and persists to snapshots JSONL.
AC7 Minimal read-only UI (/dashboard) shows health, band, latest NAV; no mutations from UI.

# Roadmap — from v0.2 to Go/No-Go

## Phase 0 (Done / Today)
- Tripwires (paper/sandbox), /plan fallback, /plan_band policy band, /snapshot_now + Scheduler (hourly).

## Phase 1 (Now)
- Fix /plan success path band override (policy).
- Remove 404 Scheduler job(s).
- Add .gitattributes to end CRLF warnings.
- Lock acceptance tests scaffolding.

## Phase 2 (Shortly)
- Minimal read-only UI (/dashboard): health, band, last NAV.
- JSONL analytics viewer (local script).

## Phase 3 (Pre Go/No-Go)
- Idempotent ledger writer + tests.
- Constraint tests (turnover/exposure/slippage).
- Kill switch: scheduler pause + traffic off script.


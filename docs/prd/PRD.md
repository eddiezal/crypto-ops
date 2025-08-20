---
version: 1.0
id: PRD-CORE
goals:
  - id: PRD-001
    title: Stream OHLCV to BigQuery
    owner: @eddie
    accepts:
      - "bq table crypto.price exists with schema v3"
      - "ingester can backfill 30d within 2h"
      - "CI job tests/ingest/test_backfill.py::test_30d passes"
  - id: PRD-002
    title: P&L / Drawdown dashboard
    accepts:
      - "looker tile shows equity curve & max DD over 30d"
      - "GET /metrics/equity returns JSON in <200ms p95"
risks:
  - "Exchange downtime or schema drift"
---

# PRD: CryptoOps Core

## Overview
Narrative description of scope, users, and success criteria.

## Non-Goals
What we are explicitly not building this phase.

## Milestones
- M1: Ingest & schema v3
- M2: Equity/Drawdown metrics + dashboard
- M3: Canary deploy & runbook
# 🛠 CryptoOps Tooling Catalog

> Keywords (for search/LLM): deploy, canary, promote, rollback, ready, traffic, status, smoke, env, STATE_BUCKET, kill switch, plan_band, plan, logs, Ready=True

## Overview

All operational scripts live in `tools/`. Use `toolbox.ps1` to run them by name.
Cloud service: **Google Cloud Run** (`cryptoops-planner` in `us-central1`).

Core endpoints:
- `/_ah/health`  — paper/sandbox + revision + hash
- `/plan_band`   — always publishes policy band (from `configs/policy.rebalancer.*`)
- `/plan`        — band + constraints; kill-switch aware (`KILL=1` or `state/kill.flag`)
- `/dashboard`   — read-only HTML (health, band, last NAV)
- `/metrics`     — plaintext metrics

Kill switch (any of the two):
- `KILL=1` env at the service level
- `state/kill.flag` object (GCS when `STATE_BUCKET` set; local file otherwise)

## Scripts

### 1) Canary + Promote (safe deploy)
**`tools/fix_plan_env_promote_safely.ps1`**  
- Canary-deploys (0% -> tag), checks `/health`, `/plan_band`, `/plan`, then shifts 100% traffic.  
- **Use when**: fixing envs (e.g., `STATE_BUCKET`), changing config without rebuilding the image.

**Keywords**: canary, promote, env, STATE_BUCKET, plan, band, Ready

### 2) Status view (service + endpoints)
**`tools/status.ps1`**  
- Prints service URL, serving revision, traffic, `/health`, `/plan_band`, `/plan` (with friendly errors + last logs tail on failure).

**Keywords**: status, health, plan, logs, traffic

### 3) Roll back traffic to last Ready=True
**`tools/rollback_to_ready.ps1`**  
- Finds newest **Ready=True** revision and pins 100% traffic to it.  
- **Use when**: newest revision fails readiness or /plan breaks.

**Keywords**: rollback, ready, traffic, pin

### 4) Safe deploy (no-traffic build->promote)
**`tools/safe_deploy.ps1`**  
- Builds a new rev with **no traffic**, waits for Ready, promotes only if healthy.  
- **Use when**: you need a source build (e.g., code change), not just env-only deploy.

**Keywords**: deploy, buildpacks, no-traffic, promote, Ready

### 5) Toolbox dispatcher
**`toolbox.ps1`**  
- Convenience wrapper: `.\toolbox.ps1 status | rollback | deploy | canary`

**Keywords**: toolbox, dispatcher, entrypoint

## Operational Recipes

- **Fix “STATE_BUCKET env var not set”**  
  Run: `.\tools\fix_plan_env_promote_safely.ps1 -StateBucket "<your-bucket>"`  
  Verifies both `/plan_band` and `/plan` before promoting.

- **“Container failed to start / Not Ready”**  
  Run: `.\tools\rollback_to_ready.ps1` to push traffic back to last good.

- **Quick sanity**  
  Run: `.\tools\status.ps1` to see health, band, plan, and serving revision.

## Notes

- All scripts assume `Service=cryptoops-planner`, `Region=us-central1`.  
- If PowerShell blocks scripts, run once per session:  
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`  
- If `gcloud` is not found, open **Google Cloud SDK Shell** once or ensure `gcloud.cmd` is on `PATH`.


### 6) Environment repair
**`tools/env_set.ps1`** — removes/readds TRADING_MODE, COINBASE_ENV, STATE_BUCKET one-by-one; waits Ready.
**Keywords**: env, concat, repair, STATE_BUCKET

### 7) Grant bucket access
**`tools/grant_bucket_access.ps1`** — grants storage.objectViewer to the service account on your state bucket.
**Keywords**: IAM, bucket, viewer

### 8) Canary smoke guard
**`tools/smoke_guard.ps1`** — blocks promote if /plan fails or bands mismatch.
**Keywords**: smoke, gate, bands

### 9) Diagnostics by revision
**`tools/diag_rev.ps1`** — prints conditions + last logs + hints.
**Keywords**: diag, logs, Ready, ModuleNotFoundError, STATE_BUCKET


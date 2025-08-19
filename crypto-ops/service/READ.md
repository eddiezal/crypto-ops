@'
# CryptoOps Planner — Windows Ops

This repo contains an HTTP planner (FastAPI on Cloud Run) plus a few helper endpoints and Cloud Scheduler/BigQuery/Monitoring setup. All commands below are Windows PowerShell friendly.

> **Prereqs**
>
> - [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (gcloud, bq)
> - You are authenticated: `gcloud auth login` and project set: `gcloud config set project <PROJECT_ID>`
> - Optional: Python 3 if you use the packaging helper (see **Packaging**).

---

## Quick start (deploy + sanity)

```powershell
# Load functions
. .\win\ops.ps1

# Initialize commonly used vars from current gcloud project
$envs = Set-OpsVars
$envs | Format-List

# Deploy (no debug endpoints in prod)
Deploy-Planner

# Get URL + token (private Cloud Run)
$u = Get-RunUrl
$t = Get-RunToken

# Health + DB hook
irm "$u/health" -Headers @{ Authorization = "Bearer $t" }
irm "$u/planner_force_dbfetch" -Headers @{ Authorization = "Bearer $t" } | % status
irm "$u/planner_debug_db" -Headers @{ Authorization = "Bearer $t" } | % db

# Plan / Dry-run / Commit
irm "$u/plan" -Headers @{ Authorization = "Bearer $t" } | Out-String
irm "$u/apply_paper?commit=0" -Headers @{ Authorization = "Bearer $t" } | Out-String
irm "$u/apply_paper?commit=1" -Headers @{ Authorization = "Bearer $t" } | Out-String

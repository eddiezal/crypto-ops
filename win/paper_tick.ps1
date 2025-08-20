# paper_tick.ps1 — one click paper “execution loop”
# 1) Pull a fresh plan from Cloud Run (with refresh)
# 2) Show a human summary
# 3) Apply latest plan (paper ledger update)

# Make sure Python uses your project + venv, even under Task Scheduler
$env:PYTHONPATH = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:VIRTUAL_ENV = (Resolve-Path (Join-Path $PSScriptRoot "..\..\.venv")).Path

Write-Host "Step 1: pull latest plan from Cloud Run (refresh=1)" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "pull_plan.ps1") -Refresh

Write-Host "`nStep 2: summarize the newest plan" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "plan_summary.ps1")

Write-Host "`nStep 3: apply latest plan (paper)" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "apply_latest_plan.ps1")

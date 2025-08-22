# KEYWORDS: diagnose, revision, conditions, logs, ModuleNotFoundError, STATE_BUCKET

param(
  [string]$Revision,
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1",
  [string]$Project = "cryptoops-sand-eddie",
  [int]$LogTail = 200
)

. "$PSScriptRoot\_common.ps1" -Service $Service -Region $Region -Project $Project
Use-Gcloud

if (-not $Revision) { $Revision = Get-LatestRevision -Svc $Service -Reg $Region }

Write-Host "== Conditions for $Revision ==" -ForegroundColor Cyan
gcloud run revisions describe $Revision --region $Region --format "yaml(status.conditions)"

Write-Host "`n== Last $LogTail log lines ==" -ForegroundColor Cyan
$logs = Tail-Logs -Svc $Service -Rev $Revision -Proj $Project -Limit $LogTail
$logs | ForEach-Object { $_ }

# Quick hints
if ($logs -match "ModuleNotFoundError: No module named 'apps.infra.state_local'") {
  Write-Host "`nHINT: ensure apps/infra/state.py conditionally imports GCS/local shim and that apps/infra/state_local.py is packaged." -ForegroundColor Yellow
}
if ($logs -match "STATE_BUCKET env var not set") {
  Write-Host "HINT: set STATE_BUCKET and grant bucket access. Try tools/env_set.ps1 + tools/grant_bucket_access.ps1" -ForegroundColor Yellow
}
if ($logs -match "Unsafe env: TRADING_MODE='") {
  Write-Host "HINT: concatenated env detected. Run tools/env_set.ps1 to remove/readd envs one-by-one." -ForegroundColor Yellow
}

Param([switch]$PlanOnly)
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root

& (Join-Path $root "win\make_plan.ps1")

if ($PlanOnly) {
  & (Join-Path $root "win\show_balances.ps1")
  & (Join-Path $root "win\run_rebalancer.ps1")
  exit 0
}

# === A4: Health gate ===
& (Join-Path $root "win\health_checks.ps1")
if ($LASTEXITCODE -ne 0) {
  Write-Host "Skipping APPLY due to health checks."
  & (Join-Path $root "win\show_balances.ps1")
  & (Join-Path $root "win\run_rebalancer.ps1")
  exit 0
}

& (Join-Path $root "win\apply_latest_plan.ps1")
& (Join-Path $root "win\show_balances.ps1")
& (Join-Path $root "win\run_rebalancer.ps1")

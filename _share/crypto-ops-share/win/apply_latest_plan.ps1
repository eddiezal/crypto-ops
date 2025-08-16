Param()
$root = Split-Path $PSScriptRoot -Parent
$plans = Get-ChildItem (Join-Path $root "plans") -Filter "plan_*.json" -File | Sort-Object LastWriteTime -Descending
if (-not $plans) { Write-Host "No plan files found."; exit 0 }
$latest = $plans[0].FullName
Write-Host "Applying latest plan:" $latest
& (Join-Path $root "win\apply_plan.ps1") -Plan $latest

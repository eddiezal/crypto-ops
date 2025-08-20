Param()
$root = Split-Path $PSScriptRoot -Parent
# Safety: require "paper"
$cfgPath = Join-Path $root "configs\policy.rebalancer.json"
$cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
$mode = $cfg.PSObject.Properties.Name -contains 'execution_mode' ? $cfg.execution_mode : 'paper'
if ($mode -ne 'paper') {
  Write-Error "Refusing to apply: execution_mode='$mode' (expected 'paper')."
  exit 2
}

$plans = Get-ChildItem (Join-Path $root "plans") -Filter "plan_*.json" -File | Sort-Object LastWriteTime -Descending
if (-not $plans) { Write-Host "No plan files found."; exit 0 }
$latest = $plans[0].FullName
Write-Host "Applying latest plan:" $latest
& (Join-Path $root "win\apply_plan.ps1") -Plan $latest

Param()
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root
$cfg = Get-Content (Join-Path $root "configs\policy.rebalancer.json") -Raw | ConvertFrom-Json
$age = [int]$cfg.risk_stops.min_price_age_sec
$maxdd = [double]$cfg.risk_stops.max_30d_drawdown
try { 
  $json = py -3 (Join-Path $root "scripts\health_checks.py") --min_age_sec $age --max_30d_dd $maxdd 
} catch { 
  $json = python (Join-Path $root "scripts\health_checks.py") --min_age_sec $age --max_30d_dd $maxdd 
}
$obj = $json | ConvertFrom-Json
if (-not $obj.ok) {
  Write-Host "Health checks FAILED."
  if ($obj.stale_symbols) { Write-Host "Stale prices (sec):" ($obj.stale_symbols | ConvertTo-Json -Compress) }
  Write-Host ("30d drawdown: {0:P2} (limit {1:P2})" -f $obj.drawdown_30d, $obj.max_30d_drawdown)
  exit 1
} else {
  Write-Host "Health checks OK."
}

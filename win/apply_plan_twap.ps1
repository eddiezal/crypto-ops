Param(
  [string]$Plan,
  [int]$Slices = 6,
  [int]$IntervalSec = 60
)
$root   = Split-Path $PSScriptRoot -Parent
$record = Join-Path $root "win\record_trade.ps1"
$health = Join-Path $root "win\health_checks.ps1"
$fetch  = Join-Path $root "win\fetch_prices_coinbase.ps1"

if (-not $Plan) {
  $latest = Get-ChildItem (Join-Path $root "plans") -Filter "plan_*.json" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $latest) { Write-Host "No plan files."; exit 1 }
  $Plan = $latest.FullName
}
$planObj = Get-Content $Plan -Raw | ConvertFrom-Json
if (-not $planObj.actions) { Write-Host "No actions in plan."; exit 0 }

for ($k=1; $k -le $Slices; $k++) {
  & $fetch | Out-Null
  & $health
  if ($LASTEXITCODE -ne 0) { Write-Warning "Health failed on slice $k — stopping."; break }

  foreach ($a in $planObj.actions) {
    $qslice = [double]$a.qty / $Slices
    if ($qslice -le 0) { continue }
    $sym  = [string]$a.symbol
    $side = [string]$a.side
    $px   = [double]($(if ($a.psobject.Properties.Name -contains 'px_eff') { $a.px_eff } else { $a.px }))
    & $record -symbol $sym -side $side -qty $qslice -px $px -fee 0 -feeAsset USD
  }

  if ($k -lt $Slices) { Start-Sleep -Seconds $IntervalSec }
}

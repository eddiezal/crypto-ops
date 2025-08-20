Param([Parameter(Mandatory=$true)][string]$Plan)
$root = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path $Plan)) { Write-Error "Plan not found: $Plan"; exit 1 }
$planObj = Get-Content $Plan -Raw | ConvertFrom-Json
if (-not $planObj.actions) { Write-Host "No actions in plan."; exit 0 }
$record = Join-Path $root "win\record_trade.ps1"
foreach ($a in $planObj.actions) {
  $sym = [string]$a.symbol
  $side = [string]$a.side
  $qty = [double]$a.qty
  $px  = [double]($(if ($a.psobject.Properties.Name -contains 'px_eff') { $a.px_eff } else { $a.px }))
  & $record -symbol $sym -side $side -qty $qty -px $px -fee 0 -feeAsset USD
}

Param(
  [Parameter(Mandatory=$true)][string]$symbol,
  [Parameter(Mandatory=$true)][ValidateSet("buy","sell")][string]$side,
  [Parameter(Mandatory=$true)][double]$qty,
  [Parameter(Mandatory=$true)][double]$px,
  [double]$fee = 0,
  [string]$feeAsset = "USD",
  [string]$account = "trading"
)

$root   = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root
$script = Join-Path $root "scripts\record_trade.py"

$al = @(
  "--account",   $account,
  "--symbol",    $symbol,
  "--side",      $side,
  "--qty",       $qty,
  "--px",        $px,
  "--fee",       $fee,
  "--fee-asset", $feeAsset
)
try { py -3 $script @al } catch { python $script @al }

Param(
  [Parameter(Mandatory=$true)][string]$symbol,
  [Parameter(Mandatory=$true)][ValidateSet("buy","sell")][string]$side,
  [Parameter(Mandatory=$true)][double]$qty,
  [Parameter(Mandatory=$true)][double]$px,
  [double]$fee = 0,
  [string]$feeAsset = "USD",
  [string]$account = "trading"
)
$root = Split-Path $PSScriptRoot -Parent
$al = @("--account",$account,"--symbol",$symbol,"--side",$side,"--qty",$qty,"--px",$px,"--fee",$fee,"--fee-asset",$feeAsset)
& (Join-Path $root "win\_python.ps1") -Script "scripts\record_trade.py" -ArgList $al

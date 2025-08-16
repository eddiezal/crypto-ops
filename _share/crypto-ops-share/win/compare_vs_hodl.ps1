Param(
  [int]$Days=120,
  [double]$RfPct=0.04,
  [double]$BTC=2,
  [double]$ETH=30,
  [double]$SOL=0,
  [double]$LINK=0,
  [double]$USD=0,
  [string]$Pairs = ""
)
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root
$script = Join-Path $root "apps\research\compare_vs_hodl.py"
$al = @("--days",$Days,"--rf",$RfPct,"--btc",$BTC,"--eth",$ETH,"--sol",$SOL,"--link",$LINK,"--usd",$USD)
if ($Pairs -ne "") { $al += @("--pairs",$Pairs) }
try { py -3 $script @al } catch { python $script @al }

Param([int]$Days=120,[double]$RfPct=0.0)
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root
$script = Join-Path $root "apps\research\backtest_rebal.py"
try { py -3 $script -- $Days $RfPct } catch { python $script -- $Days $RfPct }

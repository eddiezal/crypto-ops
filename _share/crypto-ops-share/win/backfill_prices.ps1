Param([int]$Days=120)
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root
$script = Join-Path $root "scripts\backfill_prices_coinbase.py"
try { py -3 $script $Days } catch { python $script $Days }

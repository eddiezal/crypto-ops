Param([int]$Days=120)
$root = Split-Path $PSScriptRoot -Parent
& (Join-Path $root "win\_python.ps1") -Script "scripts\backfill_prices_coinbase.py" -ArgList @($Days)

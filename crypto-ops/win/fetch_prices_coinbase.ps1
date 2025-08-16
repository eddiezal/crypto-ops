Param([string[]]$pairs=@("BTC-USD","ETH-USD","SOL-USD","LINK-USD"))
$root = Split-Path $PSScriptRoot -Parent
& (Join-Path $root "win\_python.ps1") -Script "scripts\fetch_prices_coinbase.py" -ArgList $pairs

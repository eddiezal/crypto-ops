Param([string[]]$pairs=@("BTC-USD","ETH-USD","SOL-USD","LINK-USD"))
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root
$script = Join-Path $root "scripts\fetch_prices_coinbase.py"
try { py -3 $script @pairs } catch { python $script @pairs }

Param([Parameter(Mandatory=$true)][string[]]$pairs)
$env:PYTHONPATH = "F:\CryptoOps\crypto-ops"
$argsList = @()
foreach ($p in $pairs) { $argsList += @("--pair",$p) }
try { py -3 scripts\set_prices.py @argsList } catch { python scripts\set_prices.py @argsList }

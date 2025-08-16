Param([string]$account="trading",[Parameter(Mandatory=$true)][string[]]$pairs)
$env:PYTHONPATH = "F:\CryptoOps\crypto-ops"
$al = @("--account",$account)
foreach ($p in $pairs) { $al += @("--pairs",$p) }
try { py -3 scripts\set_balances.py @al } catch { python scripts\set_balances.py @al }

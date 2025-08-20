Param([Parameter(Mandatory=$true)][string]$symbols)
$env:PYTHONPATH = "F:\CryptoOps\crypto-ops"
try { py -3 scripts\add_instruments.py --symbols $symbols } catch { python scripts\add_instruments.py --symbols $symbols }

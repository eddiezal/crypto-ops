Param()
$env:PYTHONPATH = "F:\CryptoOps\crypto-ops"
try { py -3 scripts\seed_lots_from_balances.py } catch { python scripts\seed_lots_from_balances.py }

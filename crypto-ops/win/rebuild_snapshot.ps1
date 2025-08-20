Param()
$env:PYTHONPATH = "F:\CryptoOps\crypto-ops"
try { py -3 scripts\rebuild_snapshot_after_last.py } catch { python scripts\rebuild_snapshot_after_last.py }

Param()
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force | Out-Null
try { py -3 scripts\bootstrap_db.py } catch { python scripts\bootstrap_db.py }

Param()
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force | Out-Null
try { py -3 apps\basis\main.py } catch { python apps\basis\main.py }

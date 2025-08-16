Param()
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force | Out-Null
try { py -3 ops\doctor.py }
catch { python ops\doctor.py }

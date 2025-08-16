Param()
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force | Out-Null
# Prefer 'py' if available
try { py -3 ops\post_snapshot.py }
catch { python ops\post_snapshot.py }

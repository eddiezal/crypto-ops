param([switch]$Dev)

Write-Host "[*] Creating venv..." -ForegroundColor Cyan
python -m venv .venv

if ($IsWindows) {
  . .\.venv\Scripts\Activate.ps1
} else {
  . ./.venv/bin/activate
}

python -m pip install --upgrade pip
pip install -r requirements.txt
if ($Dev) { pip install -r requirements-dev.txt }

Write-Host "[*] Done. Activate with:" -ForegroundColor Green
if ($IsWindows) { 
    Write-Host ". .\.venv\Scripts\Activate.ps1" 
} else { 
    Write-Host ". ./.venv/bin/activate" 
}
Param()
$ErrorActionPreference = "Stop"
Write-Host "==> PowerShell 7+ setup (no external Python deps)"
if (-not (Test-Path ".\.env")) {
  Copy-Item .env.example .env
  Write-Host "==> Created .env (edit with .\win\open_env.ps1)"
}
# Print Python version
try {
  py -V
} catch {
  Write-Host "WARNING: 'py' launcher not found. Try 'python --version'." -ForegroundColor Yellow
  python --version
}
Write-Host "Next steps:"
Write-Host "  1) .\win\open_env.ps1   # paste Notion token + DB IDs"
Write-Host "  2) .\win\post_snapshot.ps1   # test Notion"
Write-Host "  3) .\win\run_rebalancer.ps1  # dry-run"

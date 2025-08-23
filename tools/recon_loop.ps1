param(
  [string]$IntervalSec = "60"
)
Write-Host "Recon every $IntervalSec seconds. Ctrl+C to stop." -ForegroundColor Cyan
while ($true) {
  python .\apps\cli\recon_cb_sandbox.py
  Start-Sleep -Seconds ([int]$IntervalSec)
}

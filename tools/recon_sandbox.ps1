param(
  [string]$Project      = "cryptoops-sand-eddie",
  [string]$AbsUSD       = "25",     # absolute USD drift threshold
  [string]$Pct          = "0.5",    # percentage drift threshold for BTC/ETH
  [switch]$UseGcsState               # set this to write logs to GCS and read state there
)

# --- Fetch secrets (never echo) ---
$ErrorActionPreference = "Stop"
$env:GOOGLE_CLOUD_PROJECT = $Project
$cbKey = (gcloud secrets versions access latest --secret COINBASE_API_KEY)
$cbSec = (gcloud secrets versions access latest --secret COINBASE_API_SECRET)

if (-not $cbKey -or -not $cbSec) {
  throw "Missing Coinbase secrets in Secret Manager (COINBASE_API_KEY / COINBASE_API_SECRET)."
}

# --- Scope secrets to this process only ---
$env:COINBASE_API_KEY    = $cbKey.Trim()
$env:COINBASE_API_SECRET = $cbSec.Trim()
$env:COINBASE_ENV        = "sandbox"

# If your SDK needs explicit sandbox URL, uncomment one of these:
# $env:COINBASE_BASE_URL   = "https://api-sandbox.coinbase.com"
# $env:COINBASE_BASE_URL   = "https://api-public.sandbox.pro.coinbase.com"

# Optional: use GCS-backed state/logs for this run
if ($UseGcsState) {
  if (-not $env:STATE_BUCKET) { $env:STATE_BUCKET = "cryptoops-state-cryptoops-sand-eddie" }
}

# --- Run once; exit non-zero on drift ---
python -c "from decimal import Decimal; from apps.recon.coinbase_recon import reconcile_once; import json; print(json.dumps(reconcile_once(Decimal('$AbsUSD'), Decimal('$Pct')), indent=2))"
$code = $LASTEXITCODE
if ($code -eq 0) {
  Write-Host '✅ Recon OK (within thresholds)' -ForegroundColor Green
} else {
  Write-Host '❌ Recon drift threshold exceeded' -ForegroundColor Red
}
exit $code

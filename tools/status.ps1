param(
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1",
  [string]$Project = "cryptoops-sand-eddie",
  [int]$LogTail = 80
)

function _warn($m){ Write-Host "⚠ $m" -ForegroundColor Yellow }
function _ok($m){ Write-Host "✅ $m" -ForegroundColor Green }

$URL   = gcloud run services describe $Service --project $Project --region $Region --format "value(status.url)"
$TOKEN = gcloud auth print-identity-token
$HDR   = @{ Authorization = "Bearer $TOKEN" }

$servingRev = (gcloud run services describe $Service --project $Project --region $Region --format json | ConvertFrom-Json).status.traffic[0].revisionName

Write-Host "`n=== STATUS ($Service / $Region) ===" -ForegroundColor Cyan
Write-Host "URL: $URL"
Write-Host "Serving: $servingRev"

try {
  $h = Invoke-RestMethod "$URL/_ah/health" -Headers $HDR -TimeoutSec 15
  _ok "Health OK: $($h.trading_mode)/$($h.coinbase_env) rev=$($h.revision)"
} catch {
  _warn "Health FAILED: $_"
}

try {
  $b = Invoke-RestMethod "$URL/plan_band" -Headers $HDR -TimeoutSec 15
  _ok "Band OK: $($b.config.band)"
} catch {
  _warn "plan_band FAILED: $_"
}

try {
  $p = Invoke-RestMethod "$URL/plan" -Headers $HDR -TimeoutSec 20
  _ok "Plan OK (band=$($p.config.band))"
} catch {
  _warn "Plan FAILED, last $LogTail lines from $servingRev:"
  gcloud logging read `
    "resource.type=cloud_run_revision AND resource.labels.service_name=$Service AND resource.labels.revision_name=$servingRev" `
    --project $Project --limit $LogTail --format "value(textPayload)"
}

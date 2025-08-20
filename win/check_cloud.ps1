Param(
  [string]$Region  = "us-central1",
  [string]$Service = "cryptoops-planner"
)
$URL = gcloud run services describe $Service --region=$Region --format="value(status.url)"
if (-not $URL) { Write-Error "Cloud Run service not found in region $Region"; exit 1 }

Write-Host ("Service URL: {0}" -f $URL) -ForegroundColor Cyan

# Probe stable paths
$paths = @("/", "/health", "/readyz", "/_ah/health", "/mode", "/myip", "/plan")

foreach ($p in $paths) {
  Write-Host "`n--- GET $p ---" -ForegroundColor Yellow
  try {
    $res  = Invoke-WebRequest "$URL$p" -TimeoutSec 20 -MaximumRedirection 0 -SkipHttpErrorCheck
    $code = [int]$res.StatusCode
    "HTTP $code"
    $res.Content
  } catch {
    Write-Host "NETWORK ERROR" -ForegroundColor Red
    $_ | Out-String
  }
}

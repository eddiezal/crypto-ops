Param(
  [string]$Region  = "us-central1",
  [string]$Service = "cryptoops-planner",
  [switch]$Refresh
)

$URL = gcloud run services describe $Service --region=$Region --format="value(status.url)"
if (-not $URL) { throw "Cloud Run service not found in region $Region" }

$qs   = $Refresh ? "?refresh=1" : ""
$res  = Invoke-WebRequest "$URL/plan$qs" -TimeoutSec 30 -SkipHttpErrorCheck
if ($res.StatusCode -ge 300) {
  throw "Planner returned HTTP $($res.StatusCode): $($res.Content)"
}

$ts   = Get-Date -Format "yyyyMMdd_HHmmss"
$dir  = Join-Path $PSScriptRoot "..\plans"
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$path = Join-Path $dir ("plan_{0}.json" -f $ts)

$res.Content | Set-Content -Encoding UTF8 $path
"Saved plan to: $path"

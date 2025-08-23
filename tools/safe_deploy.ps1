# tools\safe_deploy.ps1
# Safe deploy for Cloud Run:
#  - Finds/binds gcloud.exe (works even if gcloud.ps1 is blocked by ExecutionPolicy)
#  - Pins traffic to last Ready=True rev
#  - Makes an env-only, NO-TRAFFIC revision from the same good image
#  - Waits for Ready; promotes only if healthy; otherwise prints recent logs

[CmdletBinding()]
param(
  [string]$Service     = "cryptoops-planner",
  [string]$Region      = "us-central1",
  [string]$Project     = "cryptoops-sand-eddie",
  [string]$StateBucket = "cryptoops-state-cryptoops-sand-eddie",
  [switch]$OnlyPinTraffic
)

$ErrorActionPreference = "Stop"

function Find-GcloudExe {
  # Prefer an actual EXE (ExecutionPolicy-proof)
  $candidates = @()
  try {
    $where = & where.exe gcloud 2>$null
    if ($where) { $candidates += $where -split "`r?`n" }
  } catch {}

  $searchRoots = @(
    "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin",
    "$env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin",
    "$env:ProgramFiles(x86)\Google\Cloud SDK\google-cloud-sdk\bin"
  ) | Where-Object { $_ -and (Test-Path $_) }

  foreach ($root in $searchRoots) {
    $p = Join-Path $root "gcloud.exe"
    if (Test-Path $p) { $candidates += $p }
  }

  $exe = $candidates | Where-Object { $_ -like "*.exe" } | Select-Object -First 1
  if (-not $exe) {
    throw "Could not find gcloud.exe. Please open 'Google Cloud SDK Shell' once or install the SDK, then re-run."
  }
  return $exe
}

# 1) Bind gcloud.exe for this session
$gcloud = Find-GcloudExe
Set-Alias gcloud $gcloud -Force
$null = gcloud --version

Write-Host "Using gcloud: $gcloud" -ForegroundColor Cyan
Write-Host "Service=$Service  Region=$Region  Project=$Project  STATE_BUCKET=$StateBucket" -ForegroundColor Cyan

# 2) Pin traffic to the newest Ready=True revision (safety)
$good = gcloud run revisions list `
  --service $Service --region $Region --project $Project `
  --filter "status.conditions.type=Ready AND status.conditions.status=True" `
  --format "value(metadata.name)" --limit 1

if (-not $good) { throw "No Ready=True revision found. Aborting." }

gcloud run services update-traffic $Service `
  --region $Region --project $Project `
  --to-revisions "$good=100" | Out-Null

Write-Host "Pinned traffic to Ready rev: $good" -ForegroundColor Green

if ($OnlyPinTraffic) {
  # Nothing else to do
  $url = gcloud run services describe $Service --region $Region --project $Project --format "value(status.url)"
  Write-Host "Current URL: $url" -ForegroundColor Green
  exit 0
}

# 3) Re-deploy FROM THE SAME IMAGE with safe envs, NO traffic
$img = gcloud run revisions describe $good --region $Region --project $Project --format "value(status.imageDigest)"
if (-not $img) { throw "Could not read image digest from $good." }

Write-Host "Creating no-traffic revision from image: $img" -ForegroundColor Cyan

gcloud run deploy $Service `
  --image $img `
  --region $Region `
  --project $Project `
  --no-traffic `
  --update-env-vars TRADING_MODE=paper,COINBASE_ENV=sandbox,STATE_BUCKET=$StateBucket `
  --quiet | Out-Null

# 4) Wait for Ready=True on the latest created revision
$latest = gcloud run services describe $Service --region $Region --project $Project --format "value(status.latestCreatedRevisionName)"
if (-not $latest) { throw "Could not find latestCreatedRevisionName after deploy." }

Write-Host "Waiting for revision to become Ready: $latest" -ForegroundColor Cyan
$ready = $false
1..40 | ForEach-Object {
  Start-Sleep -Seconds 3
  $st = gcloud run revisions describe $latest --region $Region --project $Project --format "value(status.conditions[?type='Ready'].status)"
  if ($st -match 'True') { $ready = $true; break }
}

if (-not $ready) {
  Write-Host "New rev $latest NOT Ready; leaving traffic on $good." -ForegroundColor Yellow
  Write-Host "`n--- Recent logs (textPayload) for $latest ---`n" -ForegroundColor Yellow
  gcloud logging read `
    "resource.type=cloud_run_revision AND resource.labels.service_name=$Service AND resource.labels.revision_name=$latest" `
    --project $Project --limit 120 --format "value(textPayload)"
  exit 1
}

# 5) Promote the new (healthy) revision
gcloud run services update-traffic $Service `
  --region $Region --project $Project `
  --to-revisions "$latest=100" | Out-Null

# 6) Show URL & a quick band smoke
$url   = gcloud run services describe $Service --region $Region --project $Project --format "value(status.url)"
$token = gcloud auth print-identity-token

Write-Host "Promoted $latest" -ForegroundColor Green
Write-Host "URL: $url" -ForegroundColor Green

try {
  $hdr = @{ Authorization = "Bearer $token" }
  $b1 = (Invoke-RestMethod "$url/plan_band" -Headers $hdr -TimeoutSec 30).config.band
  $b2 = (Invoke-RestMethod "$url/plan"      -Headers $hdr -TimeoutSec 30).config.band
  Write-Host ("Bands -> /plan_band={0}  /plan={1}" -f $b1, $b2) -ForegroundColor Green
} catch {
  Write-Host "Band smoke failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

param(
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1",
  [string]$Project = "cryptoops-sand-eddie",
  [string]$StateBucket = "cryptoops-state-cryptoops-sand-eddie"
)

$ErrorActionPreference = "Stop"

function Use-Gcloud {
  $gc = Get-Command gcloud -ErrorAction SilentlyContinue
  if (-not $gc) {
    $sdkBin = Join-Path $env:LOCALAPPDATA "Google\Cloud SDK\google-cloud-sdk\bin"
    if (Test-Path $sdkBin) { $env:PATH = "$sdkBin;$env:PATH" }
    else {
      throw "gcloud not found in PATH and default SDK path not present. Open 'Google Cloud SDK Shell' once or install the SDK."
    }
  }
}

function Get-RunToken {
  (gcloud auth print-identity-token).Trim()
}

function Get-RunUrl([string]$svc,[string]$region,[string]$proj){
  (gcloud run services describe $svc --project $proj --region $region --format "value(status.url)")
}

function Get-ServingRev([string]$svc,[string]$region,[string]$proj){
  (gcloud run services describe $svc --project $proj --region $region --format json | ConvertFrom-Json).status.traffic[0].revisionName
}

function Get-ReadyRev([string]$svc,[string]$region){
  gcloud run revisions list `
    --service $svc --region $region `
    --filter "status.conditions.type=Ready AND status.conditions.status=True" `
    --format "value(metadata.name)" --limit 1
}

function Get-ImageDigest([string]$rev,[string]$region){
  gcloud run revisions describe $rev --region $region --format "value(status.imageDigest)"
}

function Ensure-Bucket([string]$bucket,[string]$proj){
  $ls = & gsutil ls "gs://$bucket" 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Bucket gs://$bucket not found — creating..." -ForegroundColor Yellow
    & gsutil mb -p $proj "gs://$bucket"
  }
}

function Ensure-SaBucketRead([string]$svc,[string]$proj,[string]$region,[string]$bucket){
  $sa = (gcloud run services describe $svc --project $proj --region $region --format "value(spec.template.spec.serviceAccountName)").Trim()
  if (-not $sa) { $sa = "$svc-run@$proj.iam.gserviceaccount.com" }

  Write-Host "Granting objectViewer on gs://$bucket to $sa (if not already)..." -ForegroundColor Cyan
  gcloud storage buckets add-iam-policy-binding "gs://$bucket" `
    --member "serviceAccount:$sa" `
    --role "roles/storage.objectViewer" | Out-Null
}

function Wait-Ready([string]$rev,[string]$region,[int]$seconds=120){
  $tries = [Math]::Ceiling($seconds / 3)
  $ready = $false
  for ($i=1; $i -le $tries; $i++){
    Start-Sleep -Seconds 3
    $st = gcloud run revisions describe $rev --region $region --format "value(status.conditions[?type=='Ready'].status)"
    Write-Host "." -NoNewline
    if ($st -eq "True") { $ready = $true; break }
  }
  if ($ready){ Write-Host " Ready!" -ForegroundColor Green }
  return $ready
}

function Promote-IfReady([string]$svc,[string]$region,[string]$rev){
  Write-Host "Promoting $rev to 100% traffic..." -ForegroundColor Cyan
  gcloud run services update-traffic $svc --region $region --to-revisions "$rev=100"
  gcloud run services describe $svc --region $region --format "value(status.url,status.traffic)"
}

function Show-RevLogs([string]$svc,[string]$region,[string]$proj,[string]$rev,[int]$limit=120){
  Write-Host "`n--- Last $limit log lines for $rev ---" -ForegroundColor Yellow
  gcloud logging read `
    "resource.type=cloud_run_revision AND resource.labels.service_name=$svc AND resource.labels.revision_name=$rev" `
    --project $proj --limit $limit --format "value(textPayload)"
}

# --------- MAIN ---------
Use-Gcloud

# Pre-flight: ensure bucket + IAM read for runtime SA
Ensure-Bucket -bucket $StateBucket -proj $Project
Ensure-SaBucketRead -svc $Service -proj $Project -region $Region -bucket $StateBucket

# Pin to latest Ready=True before any change (safety)
$good = Get-ReadyRev -svc $Service -region $Region
if (-not $good) { throw "No Ready=True revision found; cannot proceed." }
Write-Host "Good revision: $good" -ForegroundColor Green
gcloud run services update-traffic $Service --region $Region --to-revisions "$good=100" | Out-Null

# Deploy a NO-TRAFFIC revision using the SAME IMAGE as the good rev, but with corrected envs
$img = Get-ImageDigest -rev $good -region $Region
if (-not $img) { throw "Could not read image digest for $good" }
Write-Host "Deploying new revision from image: $img" -ForegroundColor Cyan

# Keep paper/sandbox; set STATE_BUCKET
gcloud run deploy $Service `
  --image $img `
  --project $Project `
  --region $Region `
  --no-traffic `
  --update-env-vars TRADING_MODE=paper,COINBASE_ENV=sandbox,STATE_BUCKET=$StateBucket `
  --quiet

# Identify newest rev and wait for Ready
$latest = gcloud run revisions list --service $Service --region $Region --format "value(metadata.name)" --limit 1
if (-not $latest) { throw "Could not find the new revision." }

Write-Host "Waiting for $latest to become Ready (up to 120s) ..." -ForegroundColor Cyan
$ok = Wait-Ready -rev $latest -region $Region -seconds 120

if (-not $ok) {
  Write-Host "New revision is NOT Ready; leaving traffic on $good." -ForegroundColor Yellow
  Show-RevLogs -svc $Service -region $Region -proj $Project -rev $latest -limit 150
  return
}

# Promote the Ready rev
Promote-IfReady -svc $Service -region $Region -rev $latest | Out-Null

# Verify endpoints
$URL   = Get-RunUrl -svc $Service -region $Region -proj $Project
$TOKEN = Get-RunToken
$hdr   = @{ Authorization = "Bearer $TOKEN" }

Write-Host "`n--- Endpoint checks ---" -ForegroundColor Cyan
Write-Host "HEALTH:";      Invoke-RestMethod "$URL/_ah/health" -Headers $hdr | ConvertTo-Json -Depth 4
Write-Host "PLAN_BAND:";   (Invoke-RestMethod "$URL/plan_band" -Headers $hdr).config.band

Write-Host "PLAN:"; 
try {
  $plan = Invoke-RestMethod "$URL/plan?debug=1" -Headers $hdr -TimeoutSec 20
  $plan | ConvertTo-Json -Depth 6
} catch {
  Write-Host "PLAN 500 — showing build logs for the promoted revision:" -ForegroundColor Yellow
  Show-RevLogs -svc $Service -region $Region -proj $Project -rev $latest -limit 150
  throw
}

Write-Host "`nAll checks passed. Safe deploy complete → $latest" -ForegroundColor Green

param(
  [string]$Service     = "cryptoops-planner",
  [string]$Region      = "us-central1",
  [string]$Project     = "cryptoops-sand-eddie",
  [string]$StateBucket = "cryptoops-state-cryptoops-sand-eddie",
  [string]$Tag         = "canary"
)

$ErrorActionPreference = "Stop"
function _ok($msg){ Write-Host "✅ $msg" -ForegroundColor Green }
function _info($msg){ Write-Host "$msg" -ForegroundColor Cyan }
function _warn($msg){ Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function _fail($msg){ Write-Host "❌ $msg" -ForegroundColor Red; throw $msg }

# 0) Pre-flight: gcloud present?
try { gcloud --version | Out-Null } catch { _fail "gcloud not found. Open 'Google Cloud SDK Shell' once, then re-run." }

# 1) Bucket exists?
$exists = $false
try {
  gcloud storage buckets list --project $Project --format="value(name)" | Where-Object { $_ -eq "gs://$StateBucket" } | Out-Null
  if ($LASTEXITCODE -eq 0) { $exists = $true }
} catch { }
if (-not $exists) {
  _warn "Bucket gs://$StateBucket not found; creating..."
  gcloud storage buckets create "gs://$StateBucket" --project $Project --location $Region | Out-Null
}
_ok "Bucket ready: gs://$StateBucket"

# 2) Identify serving revision and image digest
$svcJson = gcloud run services describe $Service --project $Project --region $Region --format json | ConvertFrom-Json
$servingRev = $svcJson.status.traffic[0].revisionName
if (-not $servingRev) { _fail "Could not determine serving revision." }
_ok "Serving revision: $servingRev"
$img = (gcloud run revisions describe $servingRev --region $Region --format "value(status.imageDigest)")
if (-not $img) { _fail "Could not read image digest from $servingRev." }
_ok "Using image: $img"

# 3) Ensure Run service account has viewer on bucket
$sa = $svcJson.spec.template.spec.serviceAccountName
if (-not $sa) {
  $projNum = (gcloud projects describe $Project --format="value(projectNumber)")
  $sa = "$projNum-compute@developer.gserviceaccount.com"
}
_info "Granting roles/storage.objectViewer on $StateBucket to $sa (idempotent)"
gcloud storage buckets add-iam-policy-binding "gs://$StateBucket" `
  --member "serviceAccount:$sa" `
  --role "roles/storage.objectViewer" `
  --project $Project | Out-Null

# 4) Clean envs on service template (remove concatenated ghosts)
_info "Removing env vars on the service template (creates a rev with clean template)..."
gcloud run services update $Service `
  --region $Region `
  --project $Project `
  --remove-env-vars TRADING_MODE,COINBASE_ENV,STATE_BUCKET | Out-Null

# 5) Make a NO-TRAFFIC revision from the known-good image with clean envs
_info "Deploying new NO-TRAFFIC revision from known-good image with explicit envs..."
gcloud run deploy $Service `
  --image $img `
  --region $Region `
  --project $Project `
  --no-traffic `
  --update-env-vars "TRADING_MODE=paper,COINBASE_ENV=sandbox,STATE_BUCKET=$StateBucket" `
  --quiet | Out-Null

$latest = (gcloud run revisions list --service $Service --region $Region --format "value(metadata.name)" --limit 1)
if (-not $latest) { _fail "Could not find the newest revision." }
_info "Newest revision: $latest"

# 6) Tag the new revision at 0% traffic so we get a preview URL
_info "Tagging $latest as '$Tag' at 0% traffic..."
gcloud run services update-traffic $Service `
  --region $Region `
  --to-revisions "$latest=0,$servingRev=100" `
  --set-tags "$Tag=$latest" | Out-Null

# 7) Fetch the canary URL for the tag
$svcJson2 = gcloud run services describe $Service --project $Project --region $Region --format json | ConvertFrom-Json
$tagUrl = ($svcJson2.status.traffic | Where-Object { $_.tag -eq $Tag }).url
if (-not $tagUrl) { _fail "Could not find canary tag URL." }
_ok "Canary URL: $tagUrl"

# 8) Wait for Ready=True on the latest rev
_info "Waiting up to 2 minutes for the new revision to be Ready..."
$ready = $false
for ($i=1; $i -le 40; $i++) {
  Start-Sleep -Seconds 3
  $cond = (gcloud run revisions describe $latest --region $Region --format json | ConvertFrom-Json).status.conditions | Where-Object { $_.type -eq "Ready" }
  if ($cond.status -eq "True") { $ready = $true; break }
}
if (-not $ready) {
  _warn "Revision $latest NOT Ready. Leaving traffic on $servingRev."
  gcloud logging read `
    "resource.type=cloud_run_revision AND resource.labels.service_name=$Service AND resource.labels.revision_name=$latest" `
    --project $Project --limit 120 --format "value(textPayload)"
  exit 1
}
_ok "$latest is Ready=True"

# 9) Smoke test canary endpoints (no traffic impact)
$TOKEN = gcloud auth print-identity-token
$HDR   = @{ Authorization = "Bearer $TOKEN" }

function _getBand([string]$base,[string]$path){
  try { (Invoke-RestMethod "$base$path" -Headers $HDR -TimeoutSec 20).config.band }
  catch { return $null }
}

$bandPlanBand = _getBand $tagUrl "/plan_band"
if ($null -eq $bandPlanBand) { _fail "/plan_band failed on canary $tagUrl" }
_ok "Canary /plan_band OK: band=$bandPlanBand"

try {
  $plan = Invoke-RestMethod "$tagUrl/plan?debug=1" -Headers $HDR -TimeoutSec 20
  $bandPlan = $plan.config.band
  _ok "Canary /plan OK: band=$bandPlan"
}
catch {
  _warn "Canary /plan failed. Showing last 120 log lines for $latest"
  gcloud logging read `
    "resource.type=cloud_run_revision AND resource.labels.service_name=$Service AND resource.labels.revision_name=$latest" `
    --project $Project --limit 120 --format "value(textPayload)"
  exit 1
}

# 10) Promote only after successful canary test
_info "Promoting $latest to 100%..."
gcloud run services update-traffic $Service --region $Region --to-revisions "$latest=100" | Out-Null
_ok "Traffic now on $latest"

# 11) Final health checks on the service URL
$URL = gcloud run services describe $Service --project $Project --region $Region --format "value(status.url)"
"Service URL: $URL"

"HEALTH:";  (Invoke-RestMethod "$URL/_ah/health" -Headers $HDR | ConvertTo-Json -Depth 4)
"PLAN_BAND:"; (_getBand $URL "/plan_band")
try {
  "PLAN:"; (Invoke-RestMethod "$URL/plan?debug=1" -Headers $HDR -TimeoutSec 20).config.band
} catch {
  _warn ("Service /plan failed. Printing logs for {0}..." -f $latest)
  gcloud logging read `
    "resource.type=cloud_run_revision AND resource.labels.service_name=$Service AND resource.labels.revision_name=$latest" `
    --project $Project --limit 120 --format "value(textPayload)"
  exit 1
}

_ok "Done. Both endpoints good; STATE_BUCKET env clean; traffic serving $latest"

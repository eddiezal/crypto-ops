param(
  [string]$Service     = "cryptoops-planner",
  [string]$Region      = "us-central1",
  [string]$Project     = "cryptoops-sand-eddie",
  [string]$StateBucket = "cryptoops-state-cryptoops-sand-eddie",
  [switch]$SkipCanarySmoke
)

function _ok([string]$m){ Write-Host "✅ $m" -ForegroundColor Green }
function _warn([string]$m){ Write-Host "⚠ $m" -ForegroundColor Yellow }
function _err([string]$m){ Write-Host "❌ $m" -ForegroundColor Red }

function Use-Gcloud {
  if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    $sdkBin = Join-Path $env:LOCALAPPDATA "Google\Cloud SDK\google-cloud-sdk\bin"
    if (Test-Path $sdkBin) { $env:PATH = "$sdkBin;$env:PATH" }
  }
  if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "gcloud not found. Install Google Cloud SDK or open its shell."
  }
  if (-not (Get-Command gsutil -ErrorAction SilentlyContinue)) {
    throw "gsutil not found. Ensure Google Cloud SDK installed."
  }
  & gcloud --version | Out-Null
  _ok "gcloud available"
}

function Ensure-Auth {
  & gcloud config set project $Project | Out-Null
  if (-not (& gcloud auth list --filter="status:ACTIVE" --format="value(account)")) {
    & gcloud auth login | Out-Null
  }
  if (-not (& gcloud auth application-default print-access-token 2>$null)) {
    & gcloud auth application-default login | Out-Null
  }
  _ok "Authenticated to GCP as $((gcloud auth list --filter='status:ACTIVE' --format='value(account)'))"
}

function Get-ServingRev {
  (& gcloud run services describe $Service --region $Region --project $Project --format json | ConvertFrom-Json).status.traffic[0].revisionName
}

function Wait-Ready([string]$rev, [int]$seconds=120) {
  $tries = [Math]::Ceiling($seconds/3)
  for ($i=1; $i -le $tries; $i++) {
    Start-Sleep -Seconds 3
    $j = & gcloud run revisions describe $rev --region $Region --project $Project --format json | ConvertFrom-Json
    $ready = ($j.status.conditions | Where-Object { $_.type -eq "Ready" }).status
    if ($ready -eq "True") { return $true }
  }
  return $false
}

function Tail-Logs([string]$rev, [int]$limit=120) {
  & gcloud logging read `
    "resource.type=cloud_run_revision AND resource.labels.service_name=$Service AND resource.labels.revision_name=$rev" `
    --project $Project --limit $limit --format "value(textPayload)"
}

# ---- main ----
Use-Gcloud
Ensure-Auth

# a) Make sure the runtime SA can read secrets (idempotent)
$sa = (& gcloud run services describe $Service --region $Region --project $Project --format "value(spec.template.spec.serviceAccountName)")
if (-not $sa) { $sa = "$Service-run@$Project.iam.gserviceaccount.com" }
& gcloud secrets add-iam-policy-binding COINBASE_API_KEY `
  --member="serviceAccount:$sa" --role="roles/secretmanager.secretAccessor" | Out-Null
& gcloud secrets add-iam-policy-binding COINBASE_API_SECRET `
  --member="serviceAccount:$sa" --role="roles/secretmanager.secretAccessor" | Out-Null
_ok "Ensured $sa can access secrets"

# b) Use the exact image currently serving (no source rebuild risk)
$serving = Get-ServingRev
if (-not $serving) { throw "Could not determine serving revision." }
$img = & gcloud run revisions describe $serving --region $Region --project $Project --format "value(status.imageDigest)"
if (-not $img) { throw "Could not read image digest from $serving." }
_ok "Serving: $serving"
_ok "Image  : $img"

# c) Create a NO-TRAFFIC revision that binds existing secrets + envs
& gcloud run deploy $Service `
  --image $img `
  --region $Region `
  --project $Project `
  --no-traffic `
  --set-secrets "COINBASE_API_KEY=COINBASE_API_KEY:latest,COINBASE_API_SECRET=COINBASE_API_SECRET:latest" `
  --update-env-vars "TRADING_MODE=paper,COINBASE_ENV=sandbox,STATE_BUCKET=$StateBucket" `
  --quiet

$latest = & gcloud run revisions list --service $Service --region $Region --project $Project --format "value(metadata.name)" --limit 1
_ok "New revision: $latest"

# d) Wait for Ready
if (-not (Wait-Ready -rev $latest -seconds 120)) {
  _err "$latest NOT Ready after 120s; leaving traffic unchanged."
  Tail-Logs -rev $latest | Out-Host
  exit 1
}
_ok "$latest is Ready=True"

# e) Optional canary smoke (recommended)
if (-not $SkipCanarySmoke) {
  & gcloud run services update-traffic $Service `
    --region $Region --project $Project `
    --set-tags "$latest=canary" | Out-Null

  $base = (& gcloud run services describe $Service --region $Region --project $Project --format "value(status.url)")
  $canaryUrl = $base -replace '^https://','https://canary---'
  _ok "Canary URL: $canaryUrl"

  $token = (& gcloud auth print-identity-token)
  $hdr = @{ Authorization = "Bearer $token" }

  try {
    $band1 = (Invoke-RestMethod "$canaryUrl/plan_band" -Headers $hdr -TimeoutSec 20).config.band
    if ($band1 -ne 0.05) { throw "Unexpected band: $band1" }
    _ok "Canary /plan_band OK: band=$band1"

    $band2 = (Invoke-RestMethod "$canaryUrl/plan" -Headers $hdr -TimeoutSec 20).config.band
    if ($band2 -ne 0.05) { throw "Unexpected plan band: $band2" }
    _ok "Canary /plan OK: band=$band2"
  } catch {
    _err "Canary smoke failed; leaving traffic unchanged."
    Tail-Logs -rev $latest | Out-Host
    exit 1
  }
}

# f) Promote
& gcloud run services update-traffic $Service `
  --region $Region --project $Project `
  --to-revisions "$latest=100" | Out-Null
_ok "Traffic now on $latest"

# g) Final checks on primary URL
$URL   = (& gcloud run services describe $Service --region $Region --project $Project --format "value(status.url)")
$TOKEN = (& gcloud auth print-identity-token)
$HDR   = @{ Authorization = "Bearer $TOKEN" }

try {
  $h = (Invoke-RestMethod "$URL/_ah/health" -Headers $HDR -TimeoutSec 20)
  $b1 = (Invoke-RestMethod "$URL/plan_band" -Headers $HDR -TimeoutSec 20).config.band
  $b2 = (Invoke-RestMethod "$URL/plan" -Headers $HDR -TimeoutSec 20).config.band
  _ok "Health: $($h.trading_mode)/$($h.coinbase_env) state_bucket=$($h.state_bucket)"
  _ok "Band OK: $b1 and $b2"
  Write-Host "Service URL: $URL"
} catch {
  _err "Post-promotion smoke failed."
  Tail-Logs -rev $latest | Out-Host
  exit 1
}

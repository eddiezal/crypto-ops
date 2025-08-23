param(
  [Parameter(Mandatory=$false)][string]$Service      = "cryptoops-planner",
  [Parameter(Mandatory=$false)][string]$Region       = "us-central1",
  [Parameter(Mandatory=$false)][string]$Project      = "cryptoops-sand-eddie",
  [Parameter(Mandatory=$false)][string]$StateBucket  = "cryptoops-state-cryptoops-sand-eddie",
  [Parameter(Mandatory=$false)][switch]$SkipCanarySmoke  # use if you only want to wire secrets and stop
)

function _ok([string]$m)   { Write-Host "✅ $m" -ForegroundColor Green }
function _warn([string]$m) { Write-Host "⚠ $m" -ForegroundColor Yellow }
function _err([string]$m)  { Write-Host "❌ $m" -ForegroundColor Red }

function Use-Gcloud {
  # Ensure gcloud & gsutil are in PATH for this session
  $gc = Get-Command gcloud -ErrorAction SilentlyContinue
  if (-not $gc) {
    $sdkBin = Join-Path $env:LOCALAPPDATA "Google\Cloud SDK\google-cloud-sdk\bin"
    if (Test-Path $sdkBin) { $env:PATH = "$sdkBin;$env:PATH" }
  }
  if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "gcloud not found. Install Google Cloud SDK or open 'Google Cloud SDK Shell'."
  }
  if (-not (Get-Command gsutil -ErrorAction SilentlyContinue)) {
    throw "gsutil not found. Ensure Google Cloud SDK installed."
  }
  & gcloud --version | Out-Null
  _ok "gcloud available"
}

function Ensure-Auth {
  # make sure CLI and ADC are present to avoid 'Anonymous caller' with gsutil
  & gcloud config set project $Project | Out-Null
  $acct = & gcloud auth list --filter="status:ACTIVE" --format="value(account)"
  if (-not $acct) {
    _warn "No active gcloud account; launching login..."
    & gcloud auth login | Out-Null
  }
  # Application Default Credentials for gsutil
  $adc = (& gcloud auth application-default print-access-token 2>$null)
  if (-not $adc) {
    _warn "No ADC found; launching 'gcloud auth application-default login'..."
    & gcloud auth application-default login | Out-Null
  }
  _ok "Authenticated to GCP as $((gcloud auth list --filter='status:ACTIVE' --format='value(account)'))"
}

function Ensure-Secret([string]$name) {
  $exists = (& gcloud secrets describe $name --format="value(name)" 2>$null)
  if (-not $exists) {
    & gcloud secrets create $name --replication-policy="automatic" | Out-Null
    _ok "Created secret $name"
  } else {
    _ok "Secret $name exists"
  }
}

function Add-SecretVersionFromInput([string]$name, [string]$prompt) {
  # Read obscured input and add as a new secret version via a temp file
  $sec = Read-Host $prompt -AsSecureString
  $plain = [System.Net.NetworkCredential]::new("", $sec).Password
  if (-not $plain) { throw "Empty input for $name" }
  $tmp = New-TemporaryFile
  $plain | Set-Content -NoNewline -Encoding ascii $tmp.FullName
  & gcloud secrets versions add $name --data-file=$tmp.FullName | Out-Null
  Remove-Item $tmp.FullName -Force
  _ok "Added secret version for $name"
}

function Get-ServingRev {
  $j = & gcloud run services describe $Service --region $Region --project $Project --format json | ConvertFrom-Json
  return $j.status.traffic[0].revisionName
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

# ------------------ Main ------------------
Use-Gcloud
Ensure-Auth

# 0) Ensure secrets exist; add versions
Ensure-Secret "COINBASE_API_KEY"
Ensure-Secret "COINBASE_API_SECRET"

Write-Host ""
_warn "Enter your Coinbase Advanced API credentials (they will be stored in Secret Manager)."
Add-SecretVersionFromInput -name "COINBASE_API_KEY"    -prompt "COINBASE_API_KEY"
Add-SecretVersionFromInput -name "COINBASE_API_SECRET" -prompt "COINBASE_API_SECRET"

# 1) Grant secret accessor to the runtime service account
$sa = (& gcloud run services describe $Service --region $Region --project $Project --format "value(spec.template.spec.serviceAccountName)")
if (-not $sa) { $sa = "$Service-run@$Project.iam.gserviceaccount.com" }
& gcloud secrets add-iam-policy-binding COINBASE_API_KEY `
   --member="serviceAccount:$sa" --role="roles/secretmanager.secretAccessor" | Out-Null
& gcloud secrets add-iam-policy-binding COINBASE_API_SECRET `
   --member="serviceAccount:$sa" --role="roles/secretmanager.secretAccessor" | Out-Null
_ok "Granted secret accessor to $sa"

# 2) Get image digest from the currently serving revision (no source rebuild risk)
$serving = Get-ServingRev
if (-not $serving) { throw "Could not determine serving revision." }
$img = & gcloud run revisions describe $serving --region $Region --project $Project --format "value(status.imageDigest)"
if (-not $img) { throw "Could not read image digest from $serving." }
_ok "Serving: $serving"
_ok "Image  : $img"

# 3) Roll a NO-TRAFFIC revision from same image with set-secrets + envs
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

# 4) Wait for Ready
if (-not (Wait-Ready -rev $latest -seconds 120)) {
  _err "$latest NOT Ready after 120s; leaving traffic unchanged on $serving"
  Tail-Logs -rev $latest | Out-Host
  exit 1
}
_ok "$latest is Ready=True"

# 5) Canary tag & smoke (optional)
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
    $b = (Invoke-RestMethod "$canaryUrl/plan_band" -Headers $hdr -TimeoutSec 20).config.band
    if ($b -ne 0.05) { throw "Unexpected band: $b" }
    _ok "Canary /plan_band OK: band=$b"

    $p = (Invoke-RestMethod "$canaryUrl/plan" -Headers $hdr -TimeoutSec 20).config.band
    if ($p -ne 0.05) { throw "Unexpected plan band: $p" }
    _ok "Canary /plan OK: band=$p"
  } catch {
    _err "Canary smoke failed; leaving traffic unchanged."
    Tail-Logs -rev $latest | Out-Host
    exit 1
  }
}

# 6) Promote to 100% traffic
& gcloud run services update-traffic $Service `
  --region $Region --project $Project `
  --to-revisions "$latest=100" | Out-Null
_ok "Traffic now on $latest"

# 7) Final health check on primary URL
$URL = (& gcloud run services describe $Service --region $Region --project $Project --format "value(status.url)")
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

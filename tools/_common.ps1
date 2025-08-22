# KEYWORDS: common, gcloud, identity token, service url, wait ready, logs, band

param(
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1",
  [string]$Project = "cryptoops-sand-eddie"
)

function Use-Gcloud {
  $gc = Get-Command gcloud -ErrorAction SilentlyContinue
  if (-not $gc) {
    $sdkBin = Join-Path $env:LOCALAPPDATA "Google\Cloud SDK\google-cloud-sdk\bin"
    if (Test-Path $sdkBin) { $env:PATH = "$sdkBin;$env:PATH" }
  }
  $gc = Get-Command gcloud -ErrorAction SilentlyContinue
  if (-not $gc) { throw "gcloud not found. Open 'Google Cloud SDK Shell' once or add gcloud.cmd to PATH." }
}

function Get-ServiceUrl {
  param([string]$Svc,[string]$Reg,[string]$Proj)
  gcloud run services describe $Svc --project $Proj --region $Reg --format "value(status.url)"
}

function Get-ServingRevision {
  param([string]$Svc,[string]$Reg,[string]$Proj)
  (gcloud run services describe $Svc --project $Proj --region $Reg --format json | ConvertFrom-Json).status.traffic[0].revisionName
}

function Get-LatestRevision {
  param([string]$Svc,[string]$Reg)
  gcloud run revisions list --service $Svc --region $Reg --format "value(metadata.name)" --limit 1
}

function Get-ReadyRevision {
  param([string]$Svc,[string]$Reg)
  gcloud run revisions list --service $Svc --region $Reg `
    --filter "status.conditions.type=Ready AND status.conditions.status=True" `
    --format "value(metadata.name)" --limit 1
}

function Wait-RevisionReady {
  param([string]$Rev,[string]$Reg,[int]$TimeoutSec=120)
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while((Get-Date) -lt $deadline) {
    $st = gcloud run revisions describe $Rev --region $Reg --format "value(status.conditions[?type=='Ready'].status)"
    if ($st -eq 'True') { return $true }
    Start-Sleep -Seconds 3
  }
  return $false
}

function Get-AuthHeader {
  $tok = gcloud auth print-identity-token
  @{ Authorization = "Bearer $tok" }
}

function Tail-Logs {
  param([string]$Svc,[string]$Rev,[string]$Proj,[int]$Limit=120)
  gcloud logging read `
    "resource.type=cloud_run_revision AND resource.labels.service_name=$Svc AND resource.labels.revision_name=$Rev" `
    --project $Proj --limit $Limit --format "value(textPayload)"
}

function Get-PlanBand {
  param([string]$Url,[hashtable]$Hdr)
  try {
    $b = (Invoke-RestMethod "$Url/plan_band" -Headers $Hdr -TimeoutSec 15).config.band
    [double]$b
  } catch { return $null }
}

function Get-PlanBandFromPlan {
  param([string]$Url,[hashtable]$Hdr)
  try {
    $p = (Invoke-RestMethod "$Url/plan?debug=1" -Headers $Hdr -TimeoutSec 20)
    if ($p.config -and $p.config.band) { return [double]$p.config.band }
    return $null
  } catch { return $null }
}

function Ok($m){ Write-Host "✅ $m" -ForegroundColor Green }
function Warn($m){ Write-Host "⚠ $m" -ForegroundColor Yellow }
function Err($m){ Write-Host "❌ $m" -ForegroundColor Red }

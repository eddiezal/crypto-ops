# KEYWORDS: env, TRADING_MODE, COINBASE_ENV, STATE_BUCKET, Ready

param(
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1",
  [string]$Project = "cryptoops-sand-eddie",
  [string]$StateBucket = "cryptoops-state-cryptoops-sand-eddie"
)

. "$PSScriptRoot\_common.ps1" -Service $Service -Region $Region -Project $Project
Use-Gcloud

# Remove any concatenated envs in one shot
gcloud run services update $Service --region $Region `
  --project $Project --remove-env-vars TRADING_MODE,COINBASE_ENV,STATE_BUCKET `
  | Out-Null
Warn "Removed TRADING_MODE, COINBASE_ENV, STATE_BUCKET"

# Re-add one by one (each creates a new revision)
gcloud run services update $Service --region $Region --project $Project `
  --update-env-vars TRADING_MODE=paper | Out-Null
gcloud run services update $Service --region $Region --project $Project `
  --update-env-vars COINBASE_ENV=sandbox | Out-Null
gcloud run services update $Service --region $Region --project $Project `
  --update-env-vars STATE_BUCKET=$StateBucket | Out-Null
Ok "Re-added envs one-by-one"

# Wait newest rev Ready=True
$latest = Get-LatestRevision -Svc $Service -Reg $Region
if (-not $latest) { throw "Could not find latest revision." }

if (Wait-RevisionReady -Rev $latest -Reg $Region -TimeoutSec 120) {
  Ok "$latest is Ready=True"
} else {
  Err "$latest NOT Ready after 120s"
  Tail-Logs -Svc $Service -Rev $latest -Proj $Project -Limit 150
  exit 1
}

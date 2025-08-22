# KEYWORDS: bucket, IAM, service account, storage.objectViewer

param(
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1",
  [string]$Project = "cryptoops-sand-eddie",
  [string]$Bucket  = "cryptoops-state-cryptoops-sand-eddie"
)

. "$PSScriptRoot\_common.ps1" -Service $Service -Region $Region -Project $Project
Use-Gcloud

$sa = gcloud run services describe $Service --project $Project --region $Region `
  --format "value(spec.template.spec.serviceAccountName)"
if (-not $sa) { throw "Could not determine service account for $Service" }

# Create bucket if missing (non-fatal if exists)
gsutil ls "gs://$Bucket" 2>$null
if ($LASTEXITCODE -ne 0) {
  Warn "Bucket gs://$Bucket not found. Creating..."
  gsutil mb -p $Project "gs://$Bucket"
}

# Grant viewer
gcloud storage buckets add-iam-policy-binding "gs://$Bucket" `
  --member="serviceAccount:$sa" --role="roles/storage.objectViewer" | Out-Null
Ok "Granted storage.objectViewer on gs://$Bucket to $sa"

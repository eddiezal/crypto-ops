param(
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1"
)
$good = gcloud run revisions list `
  --service $Service --region $Region `
  --filter "status.conditions.type=Ready AND status.conditions.status=True" `
  --format "value(metadata.name)" --limit 1
if (-not $good) { throw "No Ready=True revision found." }
gcloud run services update-traffic $Service --region $Region --to-revisions "$good=100" | Out-Null
"Rolled back to: $good"

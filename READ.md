@'
# CryptoOps — Windows Ops Quickstart

## Prereqs
- Google Cloud CLI (`gcloud`, `bq`)
- PowerShell 7+
- Project set: `gcloud config set project <PROJECT_ID>`

## One-time setup
```powershell
Set-Location F:\CryptoOps\crypto-ops
. .\win\ops.ps1     # dot-source per shell

Deploy-CryptoOps                   # build & deploy Cloud Run
Prices-Append -Commit -Refresh    # append prices & refresh service DB
Create-SchedulerJobs              # price-append-5m, apply-paper-15m, snapshot-daily
New-BqExternalTables; New-BqViews # BigQuery external tables + views
Invoke-BqTradesLast20
Invoke-BqSnapshotsLast50

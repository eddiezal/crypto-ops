param(
  [ValidateSet("status","rollback","deploy","canary")]
  [string]$Task = "status",
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1",
  [string]$Project = "cryptoops-sand-eddie",
  [string]$StateBucket = "cryptoops-state-cryptoops-sand-eddie"
)

switch ($Task) {
  "status"   { .\tools\status.ps1 -Service $Service -Region $Region -Project $Project }
  "rollback" { .\tools\rollback_to_ready.ps1 -Service $Service -Region $Region -Project $Project }
  "deploy"   { .\tools\safe_deploy.ps1 -Service $Service -Region $Region -Project $Project }
  "canary"   { .\tools\fix_plan_env_promote_safely.ps1 -Service $Service -Region $Region -Project $Project -StateBucket $StateBucket }
}

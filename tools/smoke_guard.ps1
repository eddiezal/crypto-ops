# KEYWORDS: smoke, canary, guard, plan_band equals plan, 200, Ready

param(
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1",
  [string]$Project = "cryptoops-sand-eddie",
  [string]$UrlOverride = "",
  [double]$Tolerance = 1e-9
)

. "$PSScriptRoot\_common.ps1" -Service $Service -Region $Region -Project $Project
Use-Gcloud

$URL = if ($UrlOverride) { $UrlOverride } else { Get-ServiceUrl -Svc $Service -Reg $Region -Proj $Project }
$HDR = Get-AuthHeader

# Health
try { $h = Invoke-RestMethod "$URL/_ah/health" -Headers $HDR -TimeoutSec 15; Ok "Health OK: $($h.trading_mode)/$($h.coinbase_env)" }
catch { Err "Health FAILED: $_"; exit 1 }

# Bands
$bandPlanBand = Get-PlanBand -Url $URL -Hdr $HDR
if ($null -eq $bandPlanBand) { Err "/plan_band failed"; exit 1 }
Ok "/plan_band: band=$bandPlanBand"

$bandPlan = Get-PlanBandFromPlan -Url $URL -Hdr $HDR
if ($null -eq $bandPlan) {
  Err "/plan failed (no config.band). Dumping serving logs..."
  $servRev = Get-ServingRevision -Svc $Service -Reg $Region -Proj $Project
  Tail-Logs -Svc $Service -Rev $servRev -Proj $Project -Limit 120
  exit 1
}
Ok "/plan: band=$bandPlan"

# Compare
if ([math]::Abs($bandPlan - $bandPlanBand) -le $Tolerance) {
  Ok "Bands match within tolerance ($Tolerance)"
  exit 0
} else {
  Err "Bands mismatch: plan=$bandPlan vs plan_band=$bandPlanBand"
  exit 2
}

Param(
  [string]$Region  = "us-central1",
  [string]$Service = "cryptoops-planner"
)
$URL = gcloud run services describe $Service --region=$Region --format="value(status.url)"
$res = Invoke-WebRequest "$URL/plan" -TimeoutSec 20 -SkipHttpErrorCheck
$obj = $res.Content | ConvertFrom-Json

$n = 0
$sum = 0.0
$lines = @()

if ($obj.actions) {
  $n = $obj.actions.Count
  $sum = ($obj.actions | Measure-Object -Property usd -Sum).Sum
  foreach ($a in $obj.actions) {
    $s = "{0,-4} {1,-8} qty={2}  usd={3}" -f ($a.side.ToUpper()), $a.symbol, ([math]::Round($a.qty,6)), ([math]::Round($a.usd,2))
    $lines += $s
  }
}

"actions_count : $n"
"actions_total : $([math]::Round($sum,2))"
"band          : $($obj.config.band)"
"targets       : $((($obj.targets | ConvertTo-Json -Compress)))"
if ($lines.Count -gt 0) { "`n" + ($lines -join "`n") } else { "No actions." }

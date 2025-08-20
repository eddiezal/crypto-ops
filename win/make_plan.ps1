Param()
$root = Split-Path $PSScriptRoot -Parent

# Make a plan (same as before)
& (Join-Path $root "win\_python.ps1") -Script "apps\rebalancer\emit_plan.py"

# Log the newest plan
$plan = Get-ChildItem "$root\plans" -Filter 'plan_*.json' |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($plan) {
  & (Join-Path $root "win\_python.ps1") -Script "apps\infra\log_run.py" -ArgList @("--plan-file",$plan.FullName)
}

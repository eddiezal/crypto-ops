Param()
$root = Split-Path $PSScriptRoot -Parent
& (Join-Path $root "win\_python.ps1") -Script "apps\rebalancer\emit_plan.py"

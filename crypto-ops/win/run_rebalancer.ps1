Param([switch]$Json)
$root = Split-Path $PSScriptRoot -Parent
$al = @()
if ($Json) { $al += "--json" }
& (Join-Path $root "win\_python.ps1") -Script "apps\rebalancer\main.py" -ArgList $al

Param([string[]]$pair,[switch]$Json)
$root = Split-Path $PSScriptRoot -Parent
$al=@()
foreach ($p in $pair) { $al += @("--pair",$p) }
if ($Json) { $al += "--json" }
& (Join-Path $root "win\_python.ps1") -Script "apps\rebalancer\main.py" -ArgList $al

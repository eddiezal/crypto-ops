Param([switch]$Json)
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root
$script = Join-Path $root "apps\rebalancer\main.py"
$al = @()
if ($Json) { $al += "--json" }
try { py -3 $script @al } catch { python $script @al }

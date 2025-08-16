Param()
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root
$script = Join-Path $root "scripts\show_balances.py"
try { py -3 $script } catch { python $script }

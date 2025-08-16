Param([switch]$Json, [string[]]$pair)

$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root

$al = @()
foreach ($p in ($pair | Where-Object { $_ })) { $al += @("--pair",$p) }

# Route JSON mode to the JSON-only emitter; human mode to main.py
if ($Json) {
  & (Join-Path $root "win\_python.ps1") -Script "apps\rebalancer\emit_json.py" -ArgList $al
} else {
  & (Join-Path $root "win\_python.ps1") -Script "apps\rebalancer\main.py" -ArgList $al
}
exit $LASTEXITCODE

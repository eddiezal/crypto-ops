Param(
  [Parameter(Mandatory=$true)][string]$Script,
  [string[]]$ArgList=@()
)
$root   = Split-Path $PSScriptRoot -Parent
# venv lives one level above \crypto-ops
$venvPy = Join-Path (Split-Path $root -Parent) ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { $venvPy = "python" }
$full   = Join-Path $root $Script
& $venvPy $full @ArgList
exit $LASTEXITCODE

Param(
  [Parameter(Mandatory=$true)][string]$Script,
  [string[]]$ArgList = @()
)

$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root

# Choose Python from the active venv if available
$exe = if ($env:VIRTUAL_ENV) { Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe' } else { 'python' }

# Make the script path absolute
$full = if ([System.IO.Path]::IsPathRooted($Script)) { $Script } else { Join-Path $root $Script }

# Invoke and pass through stdout/stderr to the pipeline
& $exe $full @ArgList
exit $LASTEXITCODE

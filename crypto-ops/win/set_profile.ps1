Param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("Defensive","Balanced","Aggressive")]
  [string]$Profile,
  [double]$Alpha = 0.30,
  [int]$Days = 90,
  [switch]$DryRun,
  [switch]$NoKnobs
)
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = $root
$script = Join-Path $root "apps\research\retarget.py"
$al = @("--profile", $Profile, "--alpha", $Alpha, "--days", $Days)
if ($DryRun) { $al += "--dry-run" }
if (-not $NoKnobs) { $al += "--write-knobs" }
try { py -3 $script @al } catch { python $script @al }

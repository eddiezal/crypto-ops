param(
  [ValidateSet("status","rollback","deploy","canary","envset","grant","diag","smoke")]
  [string]$Task = "status",
  [string]$Service = "cryptoops-planner",
  [string]$Region  = "us-central1",
  [string]$Project = "cryptoops-sand-eddie",
  [string]$StateBucket = "cryptoops-state-cryptoops-sand-eddie",
  [string]$Revision = "",
  [string]$UrlOverride = ""
)

$baseDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsDir = Join-Path $baseDir "tools"

function _Normalize-Args {
  param([object]$Input)

  if ($null -eq $Input) { return @{} }
  if ($Input -is [hashtable]) { return $Input }

  # Some PS parsing paths yield Object[] even when we wrote @{...}.
  # Gather any contained hashtables into one.
  if ($Input -is [object[]]) {
    $h = @{}
    foreach($item in $Input){
      if ($item -is [hashtable]) { $h += $item }
    }
    return $h
  }

  # Last resort: try to coerce single PSCustomObject into a hashtable
  if ($Input -is [pscustomobject]) {
    $h = @{}
    $Input.PSObject.Properties | ForEach-Object { $h[$_.Name] = $_.Value }
    return $h
  }

  # Default empty map
  return @{}
}

function _Run {
  param(
    [string]$ScriptName,
    [object]$Args
  )

  $path = Join-Path $toolsDir $ScriptName
  if (-not (Test-Path $path)) { throw "Missing tool: $ScriptName ($path)" }

  $kv = _Normalize-Args -Input $Args

  # Build command line for child PowerShell
  $argList = @('-NoProfile','-ExecutionPolicy','Bypass','-File', $path)
  foreach($k in $kv.Keys){
    $v = $kv[$k]
    if ($null -ne $v -and $v -ne '') {
      $argList += @("-$k", "$v")
    }
  }

  & powershell.exe @argList
  $code = $LASTEXITCODE
  if ($code -ne 0) { throw "Tool $ScriptName failed with exit code $code" }
}

switch ($Task) {
  "status"   { _Run -ScriptName "status.ps1"                      -Args @{ Service=$Service; Region=$Region; Project=$Project } }
  "rollback" { _Run -ScriptName "rollback_to_ready.ps1"           -Args @{ Service=$Service; Region=$Region; Project=$Project } }
  "deploy"   { _Run -ScriptName "safe_deploy.ps1"                 -Args @{ Service=$Service; Region=$Region; Project=$Project } }
  "canary"   { _Run -ScriptName "fix_plan_env_promote_safely.ps1" -Args @{ Service=$Service; Region=$Region; Project=$Project; StateBucket=$StateBucket } }
  "envset"   { _Run -ScriptName "env_set.ps1"                     -Args @{ Service=$Service; Region=$Region; Project=$Project; StateBucket=$StateBucket } }
  "grant"    { _Run -ScriptName "grant_bucket_access.ps1"         -Args @{ Service=$Service; Region=$Region; Project=$Project; Bucket=$StateBucket } }
  "diag"     { _Run -ScriptName "diag_rev.ps1"                    -Args @{ Revision=$Revision; Service=$Service; Region=$Region; Project=$Project } }
  "smoke"    { _Run -ScriptName "smoke_guard.ps1"                 -Args @{ Service=$Service; Region=$Region; Project=$Project; UrlOverride=$UrlOverride } }
}

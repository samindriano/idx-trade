param(
  [Parameter(Mandatory = $true)][string]$RepoRoot,
  [Parameter(Mandatory = $true)][string]$RuntimeRoot,
  [string]$PythonExe = "python",
  [string]$TaskName = "IDXTrade-ForwardEOD",
  [string]$LegacyOpenTaskName = "IDXTrade-ForwardOpenArchive"
)

$ErrorActionPreference = "Stop"
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  throw "Scheduled task already exists: $TaskName. Refusing to replace it."
}

$resolvedRepo = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedRuntime = [IO.Path]::GetFullPath($RuntimeRoot)
$script = Join-Path $resolvedRepo "scripts/run_forward_eod_catchup.ps1"
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
  throw "Headless EOD runner is missing: $script"
}
if (-not (Test-Path -LiteralPath $resolvedRuntime -PathType Container)) {
  throw "Runtime root is missing: $resolvedRuntime"
}
if (Test-Path -LiteralPath $PythonExe -PathType Leaf) {
  $resolvedPython = (Resolve-Path -LiteralPath $PythonExe).Path
} else {
  $pythonCommand = Get-Command $PythonExe -ErrorAction Stop
  $resolvedPython = $pythonCommand.Source
}
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -RepoRoot `"$resolvedRepo`" -RuntimeRoot `"$resolvedRuntime`" -PythonExe `"$resolvedPython`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $resolvedRepo
$triggers = @(
  (New-ScheduledTaskTrigger -Daily -At "18:00"),
  (New-ScheduledTaskTrigger -AtLogOn)
)
$settings = New-ScheduledTaskSettingsSet `
  -Hidden `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
  -RunOnlyIfNetworkAvailable
$principal = New-ScheduledTaskPrincipal `
  -UserId "$env:USERNAME" `
  -LogonType Interactive `
  -RunLevel Limited

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $triggers `
  -Settings $settings `
  -Principal $principal `
  -Description "Headless IDX Trade forward EOD catch-up at 18:00; logon catch-up; canonical forward_monitoring engine."

$registered = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if (-not $registered) {
  throw "Scheduled task registration could not be verified: $TaskName"
}

# The former Open archive task is source-blocked and is superseded by the
# canonical session_ohlcv sidecar written by forward_monitoring. Disable it,
# but do not delete its task or any external artifacts.
$legacy = Get-ScheduledTask -TaskName $LegacyOpenTaskName -ErrorAction SilentlyContinue
if ($legacy) {
  Disable-ScheduledTask -TaskName $LegacyOpenTaskName -TaskPath $legacy.TaskPath | Out-Null
  $legacyAfter = Get-ScheduledTask -TaskName $LegacyOpenTaskName -TaskPath $legacy.TaskPath -ErrorAction Stop
  if ($legacyAfter.State -ne "Disabled") {
    throw "Legacy Open task was not disabled: $LegacyOpenTaskName"
  }
}

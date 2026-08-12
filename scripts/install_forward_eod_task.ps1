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

$script = Join-Path (Resolve-Path -LiteralPath $RepoRoot).Path "scripts/run_forward_eod_catchup.ps1"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -RepoRoot `"$RepoRoot`" -RuntimeRoot `"$RuntimeRoot`" -PythonExe `"$PythonExe`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $RepoRoot
$triggers = @(
  (New-ScheduledTaskTrigger -Daily -At "18:00"),
  (New-ScheduledTaskTrigger -AtLogOn)
)
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
  -RunOnlyIfNetworkAvailable
$principal = New-ScheduledTaskPrincipal `
  -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType Interactive `
  -RunLevel Limited

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $triggers `
  -Settings $settings `
  -Principal $principal `
  -Description "Headless IDX Trade forward EOD catch-up at 18:00; logon catch-up; canonical forward_monitoring engine."

# The former Open archive task is source-blocked and is superseded by the
# canonical session_ohlcv sidecar written by forward_monitoring. Disable it,
# but do not delete its task or any external artifacts.
$legacy = Get-ScheduledTask -TaskName $LegacyOpenTaskName -ErrorAction SilentlyContinue
if ($legacy) {
  Disable-ScheduledTask -TaskName $LegacyOpenTaskName -TaskPath $legacy.TaskPath | Out-Null
}

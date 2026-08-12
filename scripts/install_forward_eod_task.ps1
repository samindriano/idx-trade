param(
  [Parameter(Mandatory = $true)][string]$RepoRoot,
  [Parameter(Mandatory = $true)][string]$RuntimeRoot,
  [string]$PythonExe = "python",
  [string]$TaskName = "IDXTrade-ForwardEOD"
)

$ErrorActionPreference = "Stop"
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  throw "Scheduled task already exists: $TaskName. Refusing to replace it."
}

$script = Join-Path (Resolve-Path -LiteralPath $RepoRoot).Path "scripts/run_forward_eod_catchup.ps1"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -RepoRoot `"$RepoRoot`" -RuntimeRoot `"$RuntimeRoot`" -PythonExe `"$PythonExe`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $RepoRoot
$triggers = @(
  (New-ScheduledTaskTrigger -Daily -At "17:05"),
  (New-ScheduledTaskTrigger -Daily -At "17:30")
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
  -Description "Headless IDX Trade forward EOD catch-up; idempotent existing forward_monitoring engine."

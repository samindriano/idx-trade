param(
  [Parameter(Mandatory = $true)][string]$RepoRoot,
  [Parameter(Mandatory = $true)][string]$RuntimeRoot,
  [Parameter(Mandatory = $true)][string]$X1ModelRoot,
  [string]$PythonExe = "python",
  [string]$TaskName = "IDXTrade-ForwardEOD"
)

$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$windowsPrincipal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $windowsPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw "Administrator PowerShell is required to update scheduled task: $TaskName"
}

$resolvedRepo = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedRuntime = (Resolve-Path -LiteralPath $RuntimeRoot).Path
$resolvedModel = (Resolve-Path -LiteralPath $X1ModelRoot).Path
$pipelineScript = Join-Path $resolvedRepo "scripts\run_forward_eod_v4_x1_pipeline.ps1"
if (-not (Test-Path -LiteralPath $pipelineScript -PathType Leaf)) {
  throw "V4-X1 EOD pipeline runner is missing: $pipelineScript"
}

if (Test-Path -LiteralPath $PythonExe -PathType Leaf) {
  $resolvedPython = (Resolve-Path -LiteralPath $PythonExe).Path
} else {
  $resolvedPython = (Get-Command $PythonExe -ErrorAction Stop).Source
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$powerShellExe = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$pipelineScript`" -RepoRoot `"$resolvedRepo`" -RuntimeRoot `"$resolvedRuntime`" -X1ModelRoot `"$resolvedModel`" -PythonExe `"$resolvedPython`""

$action = New-ScheduledTaskAction `
  -Execute $powerShellExe `
  -Argument $arguments `
  -WorkingDirectory $resolvedRepo

$triggers = @(
  (New-ScheduledTaskTrigger -Daily -At "18:30"),
  (New-ScheduledTaskTrigger -Daily -At "19:30"),
  (New-ScheduledTaskTrigger -Daily -At "20:30"),
  (New-ScheduledTaskTrigger -AtLogOn)
)

$settings = New-ScheduledTaskSettingsSet `
  -Hidden `
  -StartWhenAvailable `
  -WakeToRun `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -RunOnlyIfNetworkAvailable `
  -MultipleInstances IgnoreNew `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 10) `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Set-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $triggers `
  -Settings $settings `
  -Principal $existing.Principal | Out-Null

$registered = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$registeredAction = $registered.Actions | Select-Object -First 1
if ($registeredAction.Execute -ne $powerShellExe) {
  throw "Scheduled task executable verification failed: $($registeredAction.Execute)"
}
if ($registeredAction.Arguments -notlike "*$pipelineScript*") {
  throw "Scheduled task pipeline path verification failed: $($registeredAction.Arguments)"
}
if ($registeredAction.Arguments -notlike "*$resolvedModel*") {
  throw "Scheduled task model-root verification failed: $($registeredAction.Arguments)"
}

$dailyTimes = @(
  $registered.Triggers |
    Where-Object { $_.StartBoundary } |
    ForEach-Object { ([datetime]$_.StartBoundary).ToString("HH:mm") }
)
foreach ($expected in @("18:30", "19:30", "20:30")) {
  if ($expected -notin $dailyTimes) {
    throw "Scheduled task trigger verification failed; missing $expected"
  }
}

Write-Output "TASK_UPDATE_PASS"
Write-Output "TaskName=$TaskName"
Write-Output "RepoRoot=$resolvedRepo"
Write-Output "RuntimeRoot=$resolvedRuntime"
Write-Output "X1ModelRoot=$resolvedModel"
Write-Output "PythonExe=$resolvedPython"
Write-Output "Action=$($registeredAction.Execute) $($registeredAction.Arguments)"

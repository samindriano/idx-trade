param(
  [Parameter(Mandatory = $true)][string]$RepoRoot,
  [Parameter(Mandatory = $true)][string]$RuntimeRoot,
  [string]$PythonExe = "python",
  [string]$TaskName = "IDXTrade-E2E-OfficialOpen",
  [double]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  throw "Scheduled task already exists: $TaskName. Refusing to replace it."
}

$resolvedRepo = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedRuntime = [IO.Path]::GetFullPath($RuntimeRoot)
$runner = Join-Path $resolvedRepo "scripts\run_official_open_capture.ps1"
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
  throw "Official Open runner is missing: $runner"
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

$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -RepoRoot `"$resolvedRepo`" -RuntimeRoot `"$resolvedRuntime`" -PythonExe `"$resolvedPython`" -TimeoutSeconds $TimeoutSeconds"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $resolvedRepo

# Opening auction is complete before these retries. Multiple fixed triggers are
# deliberate: source publication may lag a few minutes, and the runtime is
# idempotent after the first successful certified capture.
$triggers = @(
  (New-ScheduledTaskTrigger -Daily -At "09:02"),
  (New-ScheduledTaskTrigger -Daily -At "09:07"),
  (New-ScheduledTaskTrigger -Daily -At "09:12"),
  (New-ScheduledTaskTrigger -Daily -At "09:17"),
  (New-ScheduledTaskTrigger -Daily -At "09:22"),
  (New-ScheduledTaskTrigger -AtLogOn)
)
$settings = New-ScheduledTaskSettingsSet `
  -Hidden `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
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
  -Description "IDX Trade E2E official OpenPrice capture: direct IDX primary, Zapi raw IDX passthrough only on direct transport failure; same-session only; retries 09:02-09:22; logon catch-up; fail-closed."

$registered = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if (-not $registered) {
  throw "Scheduled task registration could not be verified: $TaskName"
}

Write-Host "Installed scheduled task: $TaskName"
Write-Host "Daily capture retries: 09:02, 09:07, 09:12, 09:17, 09:22"
Write-Host "Logon same-session catch-up: enabled"
Write-Host "Runtime root: $resolvedRuntime"
Write-Host "Transport policy: DIRECT_IDX_THEN_ZAPI_RAW_V1 (direct IDX primary; Zapi raw IDX passthrough only on direct transport failure)"

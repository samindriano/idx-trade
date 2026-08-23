[CmdletBinding()]
param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
  [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA "IDXTrade\e2e_baseline_paper_v1"),
  [string]$PythonExe = "python.exe",
  [string]$TaskName = "IDXTrade-E2E-Paper"
)

$ErrorActionPreference = "Stop"
$resolvedRepo = (Resolve-Path $RepoRoot).Path
$resolvedRuntime = [IO.Path]::GetFullPath($RuntimeRoot)
$config = Join-Path $resolvedRuntime "operational\config.json"
$configSha = Join-Path $resolvedRuntime "operational\config.json.sha256"

if (-not (Test-Path -LiteralPath $config) -or -not (Test-Path -LiteralPath $configSha)) {
  throw "E2E runtime config is missing or not hash-pinned: $resolvedRuntime"
}
$configDigest = (Get-Content -LiteralPath $configSha -Raw).Trim().ToLowerInvariant()
if ($configDigest -notmatch '^[0-9a-f]{64}$') {
  throw "E2E runtime config SHA sidecar is invalid: $resolvedRuntime"
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  throw "Scheduled task already exists: $TaskName. Refusing to replace it."
}

$python = (Get-Command $PythonExe -ErrorAction Stop).Source
$runner = Join-Path $resolvedRepo "scripts\run_e2e_paper_scheduled_v1.py"
if (-not (Test-Path -LiteralPath $runner)) { throw "Runner missing: $runner" }
$arguments = "`"$runner`" --runtime-root `"$resolvedRuntime`" --config-sha256 `"$configDigest`""
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $resolvedRepo
$triggers = @(
  (New-ScheduledTaskTrigger -Daily -At "08:30"),
  (New-ScheduledTaskTrigger -Daily -At "08:45"),
  (New-ScheduledTaskTrigger -Daily -At "09:00"),
  (New-ScheduledTaskTrigger -Daily -At "09:02"),
  (New-ScheduledTaskTrigger -Daily -At "09:07"),
  (New-ScheduledTaskTrigger -Daily -At "09:12"),
  (New-ScheduledTaskTrigger -Daily -At "09:17"),
  (New-ScheduledTaskTrigger -Daily -At "09:22"),
  # Follow the existing upstream EOD triggers (18:30/19:30/20:30)
  # so each E2E attempt runs after an upstream EOD attempt and can retry.
  (New-ScheduledTaskTrigger -Daily -At "18:35"),
  (New-ScheduledTaskTrigger -Daily -At "19:35"),
  (New-ScheduledTaskTrigger -Daily -At "20:35")
)
# A logon trigger requires elevated Task Scheduler registration on this
# machine. The daily triggers plus StartWhenAvailable provide user-level
# catch-up without weakening the runtime's own idempotency/fail-closed gates.
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings -Description "Fail-closed IDX-Trade E2E PAPER controller; config and CA authority remain external and hash-pinned." | Out-Null
$registered = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if (-not $registered.Settings.Enabled -or $registered.Principal.RunLevel -ne "Limited") {
  throw "E2E task registration verification failed: $TaskName"
}
Write-Host "Installed scheduled task: $TaskName"

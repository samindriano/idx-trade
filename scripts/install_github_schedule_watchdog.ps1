[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,

    [Parameter(Mandatory = $true)]
    [string]$StateRoot,

    [Parameter(Mandatory = $false)]
    [string]$PythonExe = "python.exe",

    [Parameter(Mandatory = $false)]
    [string]$TaskName = "IDXTrade-GitHub-Cloud-Dispatch-Watchdog"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath $RepoRoot).Path
$state = [System.IO.Path]::GetFullPath($StateRoot)
$runner = Join-Path $repo "scripts\github_schedule_watchdog_v2.py"

if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "WATCHDOG_RUNNER_MISSING"
}
if (Get-ScheduledTask -TaskName $TaskName -TaskPath "\" -ErrorAction SilentlyContinue) {
    throw "WATCHDOG_TASK_ALREADY_EXISTS"
}

# The installer never accepts, prints, or embeds the shared signing key.  The
# scheduled process must inherit a persistent user-level key configured out of
# band. This keeps the key out of Task Scheduler XML and command arguments.
$signingKey = [Environment]::GetEnvironmentVariable(
    "OFFICIAL_OPEN_SCHEDULER_HMAC_KEY",
    "User"
)
if ([string]::IsNullOrWhiteSpace($signingKey)) {
    throw "OFFICIAL_OPEN_SCHEDULER_HMAC_KEY_USER_ENV_MISSING"
}
$signingKey = $null

$resolvedPython = (Get-Command $PythonExe -ErrorAction Stop).Source
$resolvedGh = (Get-Command gh -ErrorAction Stop).Source
$user = "$env:USERDOMAIN\$env:USERNAME"
$argument = '"{0}" --repo "samindriano/idx-trade" --state-root "{1}" --gh-exe "{2}"' -f $runner, $state, $resolvedGh
$action = New-ScheduledTaskAction -Execute $resolvedPython -Argument $argument
$today = (Get-Date).Date
$triggers = @(
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(8).AddMinutes(34)),
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(8).AddMinutes(49)),
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(8).AddMinutes(59)),
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(9).AddMinutes(6)),
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(9).AddMinutes(16)),
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(9).AddMinutes(22)),
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(18).AddMinutes(40)),
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(19).AddMinutes(10)),
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(19).AddMinutes(40)),
    (New-ScheduledTaskTrigger -Daily -At $today.AddHours(20).AddMinutes(40)),
    (New-ScheduledTaskTrigger -AtLogOn)
)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -TaskPath "\" `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -User $user `
    -RunLevel Limited `
    -Description "Reversible GitHub workflow-dispatch watchdog; no provider capture." | Out-Null

Write-Output "WATCHDOG_TASK_REGISTERED=$TaskName"
Write-Output "WATCHDOG_PYTHON=$resolvedPython"
Write-Output "WATCHDOG_GH=$resolvedGh"
Write-Output "WATCHDOG_STATE_ROOT=$state"
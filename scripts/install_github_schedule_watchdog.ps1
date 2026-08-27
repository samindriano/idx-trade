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
$runner = Join-Path $repo "scripts\github_schedule_watchdog.py"

if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "WATCHDOG_RUNNER_MISSING"
}
if (Get-ScheduledTask -TaskName $TaskName -TaskPath "\" -ErrorAction SilentlyContinue) {
    throw "WATCHDOG_TASK_ALREADY_EXISTS"
}

$resolvedPython = (Get-Command $PythonExe -ErrorAction Stop).Source
$resolvedGh = (Get-Command gh -ErrorAction Stop).Source
$user = "$env:USERDOMAIN\$env:USERNAME"
$argument = '"{0}" --repo "samindriano/idx-trade" --state-root "{1}" --gh-exe "{2}"' -f $runner, $state, $resolvedGh
$action = New-ScheduledTaskAction -Execute $resolvedPython -Argument $argument
$today = (Get-Date).Date
$triggers = @(
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

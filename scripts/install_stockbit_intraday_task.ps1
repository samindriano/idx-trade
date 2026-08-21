param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string]$DataRoot,
    [string]$PythonExe = "",
    [string]$TaskName = "IDX-Trade Stockbit Intraday Daily",
    [datetime]$StartDate = (Get-Date).Date.AddDays(1),
    [switch]$AllowNonJakartaTimezone
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path $RepoRoot).Path
$runner = Join-Path $RepoRoot "scripts\run_stockbit_intraday_daily.ps1"
if (-not (Test-Path $runner)) {
    throw "Runner script not found: $runner"
}

if (-not (Test-Path $DataRoot)) {
    New-Item -ItemType Directory -Path $DataRoot -Force | Out-Null
}
$DataRoot = (Resolve-Path $DataRoot).Path

$localZone = [System.TimeZoneInfo]::Local.Id
if (-not $AllowNonJakartaTimezone -and $localZone -ne "SE Asia Standard Time") {
    throw "Windows timezone is '$localZone'. Set it to SE Asia Standard Time (WIB) or explicitly use -AllowNonJakartaTimezone."
}

$userKey = [Environment]::GetEnvironmentVariable("ZAPI_API_KEY", "User")
$machineKey = [Environment]::GetEnvironmentVariable("ZAPI_API_KEY", "Machine")
if ([string]::IsNullOrWhiteSpace($userKey) -and [string]::IsNullOrWhiteSpace($machineKey)) {
    throw "Persistent ZAPI_API_KEY was not found in User or Machine environment. The scheduler will not embed credentials."
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $PythonExe = $venvPython
    }
    else {
        $PythonExe = (Get-Command python.exe -ErrorAction Stop).Source
    }
}
if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}
$PythonExe = (Resolve-Path $PythonExe).Path

$powerShellExe = (Get-Command powershell.exe -ErrorAction Stop).Source
$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"' + $runner + '"'),
    "-RepoRoot", ('"' + $RepoRoot + '"'),
    "-DataRoot", ('"' + $DataRoot + '"'),
    "-PythonExe", ('"' + $PythonExe + '"')
) -join " "

$action = New-ScheduledTaskAction -Execute $powerShellExe -Argument $arguments -WorkingDirectory $RepoRoot
$days = @("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")

# Give the trigger an explicit future StartBoundary. This prevents registering
# the task late at night with StartWhenAvailable from being interpreted as a
# missed same-day post-close run.
$startBoundary = $StartDate.Date
if ($startBoundary -le (Get-Date).Date) {
    $startBoundary = (Get-Date).Date.AddDays(1)
}
$primaryAt = $startBoundary.AddHours(18).AddMinutes(30)
$recoveryAt = $startBoundary.AddHours(19).AddMinutes(30)
$finalRecoveryAt = $startBoundary.AddHours(20).AddMinutes(30)
$primary = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $days -At $primaryAt
$recovery = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $days -At $recoveryAt
$finalRecovery = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $days -At $finalRecoveryAt
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $currentIdentity -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger @($primary, $recovery, $finalRecovery) -Settings $settings -Principal $principal
Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Triggers: weekdays 18:30, 19:30, and 20:30 local time"
Write-Host "First trigger boundary: $($startBoundary.ToString('yyyy-MM-dd'))"
Write-Host "WakeToRun: enabled"
Write-Host "Data root: $DataRoot"
Write-Host "Python: $PythonExe"
Write-Host "Credential source: persistent ZAPI_API_KEY environment variable (value not displayed)"

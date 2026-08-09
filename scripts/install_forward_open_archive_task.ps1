param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,

    [Parameter(Mandatory = $true)]
    [string]$DataRoot,

    [string]$PythonExe = "python",
    [string]$ProviderModule = "",
    [int]$LookbackDays = 45,
    [string]$TaskName = "IDXTrade-ForwardOpenArchive",
    [string]$DailyTime = "22:00"
)

$ErrorActionPreference = "Stop"

$repo = (Resolve-Path -LiteralPath $RepoPath).Path
$runner = Join-Path $repo "scripts\run_forward_open_archive.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner script not found: $runner"
}

New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null

$escapedRunner = '"' + $runner + '"'
$escapedRepo = '"' + $repo + '"'
$escapedData = '"' + $DataRoot + '"'
$escapedPython = '"' + $PythonExe + '"'
$argument = "-NoProfile -ExecutionPolicy Bypass -File $escapedRunner -RepoPath $escapedRepo -DataRoot $escapedData -PythonExe $escapedPython -LookbackDays $LookbackDays"
if ($ProviderModule) {
    $argument += " -ProviderModule `"$ProviderModule`""
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
$daily = New-ScheduledTaskTrigger -Daily -At $DailyTime
$logon = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)

$userId = if ($env:USERDOMAIN) { "$env:USERDOMAIN\$env:USERNAME" } else { $env:USERNAME }
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger @($daily, $logon) -Settings $settings -Principal $principal

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

Write-Host "Installed scheduled task: $TaskName"
Write-Host "Daily trigger: $DailyTime local Windows time"
Write-Host "Startup/logon catch-up trigger: enabled"
Write-Host "StartWhenAvailable: enabled"
Write-Host "Provider module: $(if ($ProviderModule) { $ProviderModule } else { '<NOT FROZEN - task will fail closed>' })"
Write-Host "Data root: $DataRoot"

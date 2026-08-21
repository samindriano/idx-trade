param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string]$DataRoot,
    [string]$PythonExe = "",
    [string]$CaptureAfter = "18:00",
    [int]$MonthlyQuotaReserve = 3000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path $RepoRoot).Path
if (-not (Test-Path $DataRoot)) {
    New-Item -ItemType Directory -Path $DataRoot -Force | Out-Null
}
$DataRoot = (Resolve-Path $DataRoot).Path

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

$jakartaZone = [System.TimeZoneInfo]::FindSystemTimeZoneById("SE Asia Standard Time")
$jakartaNow = [System.TimeZoneInfo]::ConvertTime([DateTimeOffset]::Now, $jakartaZone)
$sessionDate = $jakartaNow.ToString("yyyy-MM-dd")
$finalSummary = Join-Path $DataRoot "sessions\$sessionDate\final\run_summary.json"

# The recovery trigger must be idempotent. Skip only when the policy-aware
# daily orchestrator itself completed; the lower-level farm can write an
# intermediate complete summary before policy transition, so require
# daily_run_mode to be present as well.
if (Test-Path $finalSummary) {
    try {
        $existing = Get-Content -Raw $finalSummary | ConvertFrom-Json
        $hasDailyMode = $existing.PSObject.Properties.Name -contains "daily_run_mode"
        if ($hasDailyMode -and $existing.complete -eq $true) {
            exit 0
        }
    }
    catch {
        # Let Python fail closed on any damaged/incomplete artifact state.
    }
}

$logRoot = Join-Path $DataRoot "logs"
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$stamp = $jakartaNow.ToString("yyyyMMdd_HHmmss")
$logPath = Join-Path $logRoot "stockbit_intraday_$stamp.log"

Set-Location $RepoRoot
$srcPath = Join-Path $RepoRoot "src"
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $env:PYTHONPATH = $srcPath
}
else {
    $env:PYTHONPATH = "$srcPath;$($env:PYTHONPATH)"
}

& $PythonExe -m idx_trade.stockbit_intraday_daily `
    --base-root $DataRoot `
    --capture-after $CaptureAfter `
    --monthly-quota-reserve $MonthlyQuotaReserve `
    --execute *>&1 | Tee-Object -FilePath $logPath

$exitCode = $LASTEXITCODE
exit $exitCode

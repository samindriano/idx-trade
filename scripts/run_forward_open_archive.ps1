param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,

    [Parameter(Mandatory = $true)]
    [string]$DataRoot,

    [string]$PythonExe = "python",
    [string]$ProviderModule = "",
    [int]$LookbackDays = 45
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $RepoPath)) {
    throw "Repository path does not exist: $RepoPath"
}

$logRoot = Join-Path $DataRoot "forward_open_archive\logs"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logRoot "forward-open-$stamp.log"

Push-Location $RepoPath
try {
    $arguments = @(
        "-m", "idx_trade.forward_open_archive",
        "--data-root", $DataRoot,
        "--lookback-days", "$LookbackDays"
    )
    if ($ProviderModule) {
        $arguments += @("--provider-module", $ProviderModule)
    }

    & $PythonExe @arguments *>&1 | Tee-Object -FilePath $logPath
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "Forward Open archive exited with code $exitCode. See $logPath"
    }
}
finally {
    Pop-Location
}

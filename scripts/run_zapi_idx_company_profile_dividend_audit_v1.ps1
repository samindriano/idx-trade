param(
    [string]$Code = "BBCA",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$probe = Join-Path $PSScriptRoot "probe_zapi_idx_company_profile_dividends_v1.py"
$review = Join-Path $PSScriptRoot "review_zapi_idx_company_profile_dividends_v1.py"
$anchor = Get-Date -Format "yyyyMMdd"

function Resolve-Python {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { return ,@($py.Source) }
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) { return ,@($launcher.Source, "-3") }
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($uvCmd) { return ,@($uvCmd.Source, "run", "--python", "3.13", "python") }
    foreach ($candidate in @(
        (Join-Path $HOME ".local\bin\uv.exe"),
        (Join-Path $HOME ".cargo\bin\uv.exe")
    )) {
        if (Test-Path -LiteralPath $candidate) {
            return ,@($candidate, "run", "--python", "3.13", "python")
        }
    }
    throw "Python 3 not found."
}

if (-not $OutputDir) {
    $baseOutput = "D:\Documents\Project\idx-zapi-company-profile-dividend-probe-$anchor-v1"
    $OutputDir = $baseOutput
    $revision = 2
    while (Test-Path -LiteralPath $OutputDir) {
        $OutputDir = "$baseOutput-r$revision"
        $revision += 1
    }
}
elseif (Test-Path -LiteralPath $OutputDir) {
    throw "Explicit audit output already exists and will not be overwritten: $OutputDir"
}

if (-not (Test-Path -LiteralPath $probe)) { throw "Probe script missing: $probe" }
if (-not (Test-Path -LiteralPath $review)) { throw "Reviewer script missing: $review" }

Write-Host "=== Zapi IDX company-profile dividend parity audit V1 ==="
Write-Host "Repo root:  $repoRoot"
Write-Host "Ticker:     $Code"
Write-Host "Output:     $OutputDir"
Write-Host ""
Write-Host "Audit only: no V1.1 promotion or paper-state mutation."
Write-Host "Exactly one authenticated company-profile request, zero retries."
Write-Host "PASS requires exact parity with BCA's official June 2026 Rp20 dividend schedule."
Write-Host ""

$hadKey = Test-Path Env:ZAPI_API_KEY
$temporaryKey = $false
if (-not $hadKey -or [string]::IsNullOrWhiteSpace($env:ZAPI_API_KEY)) {
    $secure = Read-Host "Zapi API key" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
    if ([string]::IsNullOrWhiteSpace($plain)) { throw "Empty Zapi API key" }
    $env:ZAPI_API_KEY = $plain
    $plain = $null
    $temporaryKey = $true
}

$python = @(Resolve-Python)
if ($python.Count -eq 0) { throw "Python command resolution returned nothing" }
$exe = [string]$python[0]
$prefix = @()
if ($python.Count -gt 1) { $prefix = @($python[1..($python.Count - 1)]) }

try {
    Write-Host "Running bounded live probe..."
    & $exe @prefix $probe --output-dir $OutputDir --code $Code
    $probeExit = $LASTEXITCODE

    $manifest = Join-Path $OutputDir "PROBE_MANIFEST.json"
    if (-not (Test-Path -LiteralPath $manifest)) { throw "Probe manifest missing: $manifest" }
    if ($probeExit -ne 0) {
        Get-Content -LiteralPath $manifest -Raw
        throw "company-profile probe failed (exit $probeExit). V1.1 remains blocked."
    }

    Write-Host ""
    Write-Host "Running offline parity reviewer..."
    & $exe @prefix $review --probe-dir $OutputDir
    $reviewExit = $LASTEXITCODE

    $report = Join-Path $OutputDir "PROBE_REVIEW.json"
    if (-not (Test-Path -LiteralPath $report)) { throw "Review report missing: $report" }

    if ($reviewExit -eq 0) {
        Write-Host ""
        Write-Host "Zapi company-profile dividend audit PASS candidate." -ForegroundColor Green
        Write-Host "Report: $report"
        Write-Host "Paste the JSON review output back to ChatGPT. Do not wire V1.1 manually."
    }
    else {
        Write-Host ""
        Write-Host "Zapi company-profile dividend audit FAIL. V1.1 remains blocked." -ForegroundColor Yellow
        Write-Host "Report: $report"
        throw "company-profile semantic/parity review failed (exit $reviewExit)."
    }
}
finally {
    if ($temporaryKey) { Remove-Item Env:ZAPI_API_KEY -ErrorAction SilentlyContinue }
}

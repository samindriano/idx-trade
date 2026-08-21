param(
    [string]$Code = "BBCA",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$probe = Join-Path $PSScriptRoot "probe_zapi_idx_dividends_v1.py"
$review = Join-Path $PSScriptRoot "review_zapi_idx_dividends_probe_v1.py"
$anchor = Get-Date -Format "yyyyMMdd"

function Resolve-Python {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { return @($py.Source) }
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) { return @($launcher.Source, "-3") }
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) {
        foreach ($candidate in @(
            (Join-Path $HOME ".local\bin\uv.exe"),
            (Join-Path $HOME ".cargo\bin\uv.exe")
        )) {
            if (Test-Path -LiteralPath $candidate) { $uv = Get-Item $candidate; break }
        }
    }
    if ($uv) { return @($uv.FullName, "run", "--with", "python-dateutil", "python") }
    throw "Python 3 not found. The previous Forward-CA setup normally installs uv/Python; rerun setup_idx_bei_forward_ca_provider.ps1 if needed."
}

if (-not $OutputDir) {
    $OutputDir = "D:\Documents\Project\idx-zapi-dividends-probe-$anchor-v1"
}
if (Test-Path -LiteralPath $OutputDir) {
    throw "Audit output already exists and will not be overwritten: $OutputDir"
}
if (-not (Test-Path -LiteralPath $probe)) { throw "Probe script missing: $probe" }
if (-not (Test-Path -LiteralPath $review)) { throw "Reviewer script missing: $review" }

Write-Host "=== Zapi IDX /dividends bounded audit V1 ==="
Write-Host "Repo root:  $repoRoot"
Write-Host "Ticker:     $Code"
Write-Host "Output:     $OutputDir"
Write-Host ""
Write-Host "Audit only: no V1.1 promotion, no paper-state mutation, no retries."
Write-Host "The runner performs one public catalog-schema request and at most one authenticated /dividends request."
Write-Host ""

$hadKey = Test-Path Env:ZAPI_API_KEY
$temporaryKey = $false
if (-not $hadKey -or [string]::IsNullOrWhiteSpace($env:ZAPI_API_KEY)) {
    Write-Host "ZAPI_API_KEY is not set. Enter your Zapi API key locally. It will not be printed or written to disk."
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

$python = Resolve-Python
$exe = $python[0]
$prefix = @()
if ($python.Count -gt 1) { $prefix = $python[1..($python.Count - 1)] }

try {
    Write-Host "Running bounded live probe..."
    & $exe @prefix $probe --output-dir $OutputDir --code $Code
    $probeExit = $LASTEXITCODE

    $manifest = Join-Path $OutputDir "PROBE_MANIFEST.json"
    if (-not (Test-Path -LiteralPath $manifest)) {
        throw "Probe manifest missing after probe: $manifest"
    }

    if ($probeExit -ne 0) {
        Write-Host ""
        Write-Host "Probe did not reach an admissible completed response. Manifest:" -ForegroundColor Yellow
        Get-Content -LiteralPath $manifest -Raw
        throw "Zapi dividends probe failed before offline review (exit $probeExit). V1.1 remains blocked."
    }

    Write-Host ""
    Write-Host "Running offline semantic reviewer (no network request)..."
    & $exe @prefix $review --probe-dir $OutputDir
    $reviewExit = $LASTEXITCODE

    $report = Join-Path $OutputDir "PROBE_REVIEW.json"
    if (-not (Test-Path -LiteralPath $report)) {
        throw "Review report missing: $report"
    }

    Write-Host ""
    if ($reviewExit -eq 0) {
        Write-Host "Zapi dividends audit PASS candidate." -ForegroundColor Green
        Write-Host "Report: $report"
        Write-Host "Paste the JSON review output back to ChatGPT. Do not wire V1.1 manually."
    }
    else {
        Write-Host "Zapi dividends audit FAIL. V1.1 must NOT be created from this endpoint yet." -ForegroundColor Yellow
        Write-Host "Report: $report"
        throw "Zapi dividends semantic review failed (exit $reviewExit)."
    }
}
finally {
    if ($temporaryKey) {
        Remove-Item Env:ZAPI_API_KEY -ErrorAction SilentlyContinue
    }
}

param(
    [string]$ProviderCheckout = "D:\Documents\Project\idx-bei-forward-ca-provider",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$setup = Join-Path $PSScriptRoot "setup_idx_bei_forward_ca_provider.ps1"
$probe = Join-Path $PSScriptRoot "probe_forward_ca_idx_dividend_current_pair_v1.py"
$review = Join-Path $PSScriptRoot "review_forward_ca_idx_dividend_current_pair_v1.py"
$anchor = Get-Date -Format "yyyyMMdd"

if (-not $OutputDir) {
    $base = "D:\Documents\Project\idx-forward-ca-current-dividend-pair-$anchor-v1"
    $OutputDir = $base
    $n = 2
    while (Test-Path -LiteralPath $OutputDir) {
        $OutputDir = "$base-r$n"
        $n += 1
    }
}
elseif (Test-Path -LiteralPath $OutputDir) {
    throw "Output already exists: $OutputDir"
}

if (-not (Test-Path -LiteralPath $setup)) { throw "Provider setup script missing: $setup" }
if (-not (Test-Path -LiteralPath $probe)) { throw "Probe script missing: $probe" }
if (-not (Test-Path -LiteralPath $review)) { throw "Review script missing: $review" }

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    foreach ($candidate in @((Join-Path $HOME ".local\bin\uv.exe"), (Join-Path $HOME ".cargo\bin\uv.exe"))) {
        if (Test-Path -LiteralPath $candidate) { $uv = Get-Item $candidate; break }
    }
}
if (-not $uv) { throw "uv not found" }
$uvExe = $uv.Source
if (-not $uvExe) { $uvExe = $uv.FullName }

Write-Host "=== Forward CA current dividend paired direct-IDX audit V1 ==="
Write-Host "Provider checkout: $ProviderCheckout"
Write-Host "Target:            BBCA / August 2026"
Write-Host "Output:            $OutputDir"
Write-Host ""
Write-Host "Exactly two direct official IDX requests, zero retries:"
Write-Host "1) LINK_DIVIDEND August 2026 search=BBCA"
Write-Host "2) BBCA announcements 2026-08-18..2026-08-21"
Write-Host "No Zapi request. No paper-state mutation."
Write-Host ""

& $setup -Checkout $ProviderCheckout
if ($LASTEXITCODE -ne 0) { throw "Provider setup failed (exit $LASTEXITCODE)" }

$providerProject = Join-Path $ProviderCheckout "python"
Write-Host "Running paired direct IDX probe..."
& $uvExe run --project $providerProject python $probe `
    --provider-checkout $ProviderCheckout `
    --output-dir $OutputDir `
    --code BBCA `
    --year 2026 `
    --month 8 `
    --announcement-from 2026-08-18 `
    --announcement-through 2026-08-21
$probeExit = $LASTEXITCODE
if ($probeExit -ne 0) { throw "paired direct IDX probe failed (exit $probeExit)" }

Write-Host ""
Write-Host "Running offline paired review..."
& $uvExe run --project $providerProject python $review --probe-dir $OutputDir
$reviewExit = $LASTEXITCODE

$report = Join-Path $OutputDir "PROBE_REVIEW.json"
if (-not (Test-Path -LiteralPath $report)) { throw "Review report missing: $report" }

if ($reviewExit -eq 0) {
    Write-Host ""
    Write-Host "Direct IDX current dividend pair PASS candidate." -ForegroundColor Green
    Write-Host "Report: $report"
}
else {
    Write-Host ""
    Write-Host "Direct IDX current dividend pair FAIL; do not promote V1.1 yet." -ForegroundColor Yellow
    Write-Host "Report: $report"
    throw "paired direct IDX semantic review failed (exit $reviewExit)"
}

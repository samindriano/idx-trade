param(
    [string]$ProviderCheckout = "D:\Documents\Project\idx-bei-forward-ca-provider",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$setup = Join-Path $PSScriptRoot "setup_idx_bei_forward_ca_provider.ps1"
$probe = Join-Path $PSScriptRoot "probe_forward_ca_idx_dividend_current_pair_v2.py"
$review = Join-Path $PSScriptRoot "review_forward_ca_idx_dividend_current_pair_v2.py"
$anchor = Get-Date -Format "yyyyMMdd"

if (-not $OutputDir) {
    $base = "D:\Documents\Project\idx-forward-ca-current-dividend-pair-v2-$anchor-v1"
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

foreach ($path in @($setup, $probe, $review)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required script missing: $path" }
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    foreach ($candidate in @((Join-Path $HOME ".local\bin\uv.exe"), (Join-Path $HOME ".cargo\bin\uv.exe"))) {
        if (Test-Path -LiteralPath $candidate) { $uv = Get-Item $candidate; break }
    }
}
if (-not $uv) { throw "uv not found" }
$uvExe = $uv.Source
if (-not $uvExe) { $uvExe = $uv.FullName }

Write-Host "=== Forward CA current dividend paired direct-IDX audit V2 ==="
Write-Host "Provider checkout: $ProviderCheckout"
Write-Host "Target:            BBCA / current Aug-Sep 2026 dividend"
Write-Host "Output:            $OutputDir"
Write-Host ""
Write-Host "Exactly two direct official IDX HTTP attempts, no retry helper:"
Write-Host "1) LINK_DIVIDEND August 2026 search=BBCA"
Write-Host "2) ListedCompany/GetAnnouncement BBCA 2026-08-18..2026-08-21"
Write-Host "No Zapi request. No paper-state mutation."
Write-Host ""

& $setup -Checkout $ProviderCheckout
if ($LASTEXITCODE -ne 0) { throw "Provider setup failed (exit $LASTEXITCODE)" }

$providerProject = Join-Path $ProviderCheckout "python"
Write-Host "Running paired direct IDX V2 probe..."
& $uvExe run --project $providerProject python $probe `
    --provider-checkout $ProviderCheckout `
    --output-dir $OutputDir `
    --code BBCA
$probeExit = $LASTEXITCODE
if ($probeExit -ne 0) {
    throw "paired direct IDX V2 probe failed (exit $probeExit)"
}

Write-Host ""
Write-Host "Running offline V2 review..."
& $uvExe run --project $providerProject python $review --probe-dir $OutputDir
$reviewExit = $LASTEXITCODE

$report = Join-Path $OutputDir "PROBE_REVIEW.json"
if (-not (Test-Path -LiteralPath $report)) { throw "Review report missing: $report" }

if ($reviewExit -eq 0) {
    Write-Host ""
    Write-Host "Direct IDX current dividend pair V2 PASS candidate." -ForegroundColor Green
    Write-Host "Report: $report"
}
else {
    Write-Host ""
    Write-Host "Direct IDX current dividend pair V2 FAIL; do not promote V1.1 yet." -ForegroundColor Yellow
    Write-Host "Report: $report"
    throw "paired direct IDX V2 semantic review failed (exit $reviewExit)"
}

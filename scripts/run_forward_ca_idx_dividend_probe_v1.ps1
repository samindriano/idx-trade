param(
    [string]$ProviderCheckout = "D:\Documents\Project\idx-bei-forward-ca-provider",
    [int]$Year = 2026,
    [int]$Month = 3,
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$setup = Join-Path $PSScriptRoot "setup_idx_bei_forward_ca_provider.ps1"
$probe = Join-Path $PSScriptRoot "probe_forward_ca_idx_dividend_v1.py"
$review = Join-Path $PSScriptRoot "review_forward_ca_idx_dividend_probe_v1.py"
$providerProject = Join-Path $ProviderCheckout "python"
$anchor = Get-Date -Format "yyyyMMdd"

function Resolve-UvExecutable {
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in @(
        (Join-Path $HOME ".local\bin\uv.exe"),
        (Join-Path $HOME ".cargo\bin\uv.exe")
    )) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $null
}

if (-not $OutputDir) {
    $baseOutput = "D:\Documents\Project\idx-forward-ca-direct-dividend-probe-$anchor-$Year-$('{0:D2}' -f $Month)-v1"
    $OutputDir = $baseOutput
    $revision = 2
    while (Test-Path -LiteralPath $OutputDir) {
        $OutputDir = "$baseOutput-r$revision"
        $revision += 1
    }
}
elseif (Test-Path -LiteralPath $OutputDir) {
    throw "Explicit output already exists: $OutputDir"
}

Write-Host "=== Forward CA Direct IDX Dividend Probe V1 ==="
Write-Host "Provider checkout: $ProviderCheckout"
Write-Host "Known-positive:     $Year-$('{0:D2}' -f $Month)"
Write-Host "Output:             $OutputDir"
Write-Host ""
Write-Host "One direct official IDX LINK_DIVIDEND request, zero retries."
Write-Host "No Zapi request. No paper-state mutation. No V1.1 promotion by the runner."
Write-Host ""

& $setup -Checkout $ProviderCheckout
if ($LASTEXITCODE -ne 0) { throw "provider setup failed" }
$uv = Resolve-UvExecutable
if (-not $uv) { throw "uv executable not found after provider setup" }
if (-not (Test-Path -LiteralPath $probe)) { throw "probe missing: $probe" }
if (-not (Test-Path -LiteralPath $review)) { throw "reviewer missing: $review" }

Write-Host "Running one direct IDX dividend probe..."
& $uv run --project $providerProject python $probe `
    --provider-checkout $ProviderCheckout `
    --year $Year `
    --month $Month `
    --output-dir $OutputDir `
    --page-size 100
$probeExit = $LASTEXITCODE
if ($probeExit -ne 0) {
    throw "direct IDX dividend probe failed (exit $probeExit)"
}

Write-Host ""
Write-Host "Running offline parity review..."
& $uv run --project $providerProject python $review --probe-dir $OutputDir
$reviewExit = $LASTEXITCODE
$report = Join-Path $OutputDir "PROBE_REVIEW.json"
if (-not (Test-Path -LiteralPath $report)) { throw "review report missing: $report" }

Write-Host ""
if ($reviewExit -eq 0) {
    Write-Host "Direct IDX dividend source PASS candidate." -ForegroundColor Green
    Write-Host "Report: $report"
    Write-Host "Paste the JSON review output back to ChatGPT. Do not promote V1.1 manually."
}
else {
    Write-Host "Direct IDX dividend source FAIL; V1.1 remains blocked." -ForegroundColor Yellow
    Write-Host "Report: $report"
    throw "direct IDX dividend semantic review failed (exit $reviewExit)"
}

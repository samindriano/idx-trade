param(
    [string]$ProviderCheckout = "D:\Documents\Project\idx-bei-forward-ca-provider",
    [string]$ProbeDir = "D:\Documents\Project\idx-forward-ca-current-dividend-pair-v2-20260821-v1",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$setup = Join-Path $PSScriptRoot "setup_idx_bei_forward_ca_provider.ps1"
$capture = Join-Path $PSScriptRoot "capture_forward_ca_idx_dividend_attachments_v1.py"
$review = Join-Path $PSScriptRoot "review_forward_ca_idx_dividend_attachments_v1.py"
$anchor = Get-Date -Format "yyyyMMdd"

if (-not $OutputDir) {
    $base = "D:\Documents\Project\idx-forward-ca-dividend-attachments-$anchor-v1"
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

foreach ($path in @($setup, $capture, $review)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required script missing: $path" }
}
if (-not (Test-Path -LiteralPath (Join-Path $ProbeDir "announcements.json"))) {
    throw "Existing V2 announcements artifact missing: $ProbeDir\announcements.json"
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

Write-Host "=== Forward CA Direct IDX Dividend Attachment Audit V1 ==="
Write-Host "Existing probe:      $ProbeDir"
Write-Host "Provider checkout:   $ProviderCheckout"
Write-Host "Output:              $OutputDir"
Write-Host ""
Write-Host "Uses the already captured official IDX announcement metadata."
Write-Host "Downloads only the three attachment URLs listed in that exact BBCA announcement, one HTTP attempt each, no retries."
Write-Host "No LINK_DIVIDEND request. No Zapi request. No paper-state mutation."
Write-Host ""

& $setup -Checkout $ProviderCheckout
if ($LASTEXITCODE -ne 0) { throw "Provider setup failed (exit $LASTEXITCODE)" }

$providerProject = Join-Path $ProviderCheckout "python"
Write-Host "Capturing official IDX attachment PDFs..."
& $uvExe run --project $providerProject python $capture `
    --provider-checkout $ProviderCheckout `
    --probe-dir $ProbeDir `
    --output-dir $OutputDir
$captureExit = $LASTEXITCODE
if ($captureExit -ne 0) { throw "attachment capture failed (exit $captureExit)" }

Write-Host ""
Write-Host "Running offline PDF semantic review..."
python $review --attachment-dir $OutputDir
$reviewExit = $LASTEXITCODE

$report = Join-Path $OutputDir "ATTACHMENT_REVIEW.json"
if (-not (Test-Path -LiteralPath $report)) { throw "Attachment review report missing: $report" }

if ($reviewExit -eq 0) {
    Write-Host ""
    Write-Host "Direct IDX announcement + attachment terms PASS candidate." -ForegroundColor Green
    Write-Host "Report: $report"
}
else {
    Write-Host ""
    Write-Host "Attachment terms review FAIL; do not promote V1.1 yet." -ForegroundColor Yellow
    Write-Host "Report: $report"
    throw "attachment semantic review failed (exit $reviewExit)"
}

param(
    [string]$ProviderCheckout = "D:\Documents\Project\idx-bei-forward-ca-provider",
    [string]$AnchorDate = (Get-Date -Format "yyyyMMdd"),
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$setup = Join-Path $PSScriptRoot "setup_idx_bei_forward_ca_provider.ps1"
$probe = Join-Path $PSScriptRoot "probe_forward_ca_calendar_schema_v1.py"
$providerProject = Join-Path $ProviderCheckout "python"

if (-not $OutputDir) {
    $OutputDir = "D:\Documents\Project\idx-forward-ca-calendar-probe-$AnchorDate-v1"
}

if (Test-Path -LiteralPath $OutputDir) {
    throw "Probe output already exists and will not be overwritten: $OutputDir"
}

& $setup -Checkout $ProviderCheckout
if ($LASTEXITCODE -ne 0) { throw "provider setup failed" }

if (-not (Test-Path -LiteralPath $providerProject)) {
    throw "provider python project missing: $providerProject"
}

Write-Host "Running exactly one bounded direct-IDX Home/GetCalendar probe..."
uv run --project $providerProject python $probe `
    --provider-checkout $ProviderCheckout `
    --date $AnchorDate `
    --output-dir $OutputDir
if ($LASTEXITCODE -ne 0) { throw "calendar probe failed" }

$manifest = Join-Path $OutputDir "PROBE_MANIFEST.json"
if (-not (Test-Path -LiteralPath $manifest)) {
    throw "probe manifest missing: $manifest"
}

Write-Host ""
Write-Host "Forward CA calendar probe complete."
Write-Host "Manifest: $manifest"
Write-Host "Raw bytes remain external and immutable under: $OutputDir"
Write-Host "Do NOT pin/promote the fingerprint before independent review."

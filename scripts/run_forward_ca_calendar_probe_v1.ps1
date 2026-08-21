param(
    [string]$ProviderCheckout = "D:\Documents\Project\idx-bei-forward-ca-provider",
    [string]$AnchorDate = (Get-Date -Format "yyyyMMdd"),
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$setup = Join-Path $PSScriptRoot "setup_idx_bei_forward_ca_provider.ps1"
$probe = Join-Path $PSScriptRoot "probe_forward_ca_calendar_schema_v1.py"
$providerProject = Join-Path $ProviderCheckout "python"

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
    $OutputDir = "D:\Documents\Project\idx-forward-ca-calendar-probe-$AnchorDate-v1"
}

if (Test-Path -LiteralPath $OutputDir) {
    throw "Probe output already exists and will not be overwritten: $OutputDir"
}

Write-Host "=== Forward CA Calendar Probe V1 ==="
Write-Host "Repo root:         $repoRoot"
Write-Host "Provider checkout: $ProviderCheckout"
Write-Host "Anchor date:       $AnchorDate"
Write-Host "Output:            $OutputDir"
Write-Host ""

& $setup -Checkout $ProviderCheckout
if ($LASTEXITCODE -ne 0) { throw "provider setup failed" }

$uv = Resolve-UvExecutable
if (-not $uv) {
    throw "uv was installed/prepared by setup but cannot be resolved by runner"
}

if (-not (Test-Path -LiteralPath $providerProject)) {
    throw "provider python project missing: $providerProject"
}
if (-not (Test-Path -LiteralPath $probe)) {
    throw "probe script missing: $probe"
}

Write-Host ""
Write-Host "Running exactly ONE bounded direct-IDX Home/GetCalendar request..."
& $uv run --project $providerProject python $probe `
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
Write-Host "Raw bytes: $OutputDir\calendar_raw.json"
Write-Host ""
Write-Host "Copy the full terminal output and PROBE_MANIFEST.json back to ChatGPT."
Write-Host "Do NOT pin/promote the fingerprint manually."

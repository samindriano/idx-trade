param(
    [string]$ProbeDir = "D:\Documents\Project\idx-forward-ca-calendar-probe-20260821-v1",
    [string]$ProviderCheckout = "D:\Documents\Project\idx-bei-forward-ca-provider"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$reviewer = Join-Path $PSScriptRoot "review_forward_ca_calendar_probe_v1.py"
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
    throw "uv.exe not found. Forward CA setup should already have installed it."
}

if (-not (Test-Path -LiteralPath $ProbeDir)) {
    throw "Probe directory missing: $ProbeDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $ProbeDir "PROBE_MANIFEST.json"))) {
    throw "PROBE_MANIFEST.json missing under: $ProbeDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $ProbeDir "calendar_raw.json"))) {
    throw "calendar_raw.json missing under: $ProbeDir"
}
if (-not (Test-Path -LiteralPath $providerProject)) {
    throw "Pinned provider environment missing: $providerProject"
}

$uv = Resolve-UvExecutable
Write-Host "=== Forward CA Calendar Probe Review V1 ==="
Write-Host "Probe dir: $ProbeDir"
Write-Host "Reviewer:  $reviewer"
Write-Host "Using uv:  $uv"
Write-Host ""
Write-Host "This is OFFLINE review only. No IDX/Zapi request will be made."
Write-Host ""

& $uv run --project $providerProject python $reviewer --probe-dir $ProbeDir
$exit = $LASTEXITCODE
if ($exit -ne 0) {
    throw "Forward CA probe review FAILED with exit code $exit. Do not freeze the fingerprint."
}

$report = Join-Path $ProbeDir "PROBE_REVIEW.json"
if (-not (Test-Path -LiteralPath $report)) {
    throw "Review report missing: $report"
}

Write-Host ""
Write-Host "Forward CA calendar probe review PASS."
Write-Host "Report: $report"
Write-Host "No network request was made by this review step."
Write-Host "Copy the JSON printed above back to ChatGPT for final schema-freeze review."

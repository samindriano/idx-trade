param(
  [Parameter(Mandatory = $true)][string]$RepoRoot,
  [Parameter(Mandatory = $true)][string]$RuntimeRoot,
  [Parameter(Mandatory = $true)][string]$X1ModelRoot,
  [Parameter(Mandatory = $true)][string]$CleanPanel,
  [Parameter(Mandatory = $true)][string]$CleanSecurityMaster,
  [string]$PythonExe = "python",
  [int]$BatchSize = 100,
  [string]$ObservedBy = "2026-08-20T12:08:44+00:00"
)

$ErrorActionPreference = "Stop"
$resolvedRepo = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedRuntime = [IO.Path]::GetFullPath($RuntimeRoot)
$resolvedModel = (Resolve-Path -LiteralPath $X1ModelRoot).Path
$resolvedPanel = (Resolve-Path -LiteralPath $CleanPanel).Path
$resolvedMaster = (Resolve-Path -LiteralPath $CleanSecurityMaster).Path
$src = Join-Path $resolvedRepo "src"
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($previousPythonPath) { "$src;$previousPythonPath" } else { $src }
$env:PYTHONUNBUFFERED = "1"

& $PythonExe -m idx_trade.v4_x1_clean_eod_legacy_compat `
  --runtime-root $resolvedRuntime `
  --x1-model-root $resolvedModel `
  --clean-panel $resolvedPanel `
  --clean-security-master $resolvedMaster `
  --repo-root $resolvedRepo `
  --batch-size $BatchSize `
  --observed-by $ObservedBy

exit $LASTEXITCODE

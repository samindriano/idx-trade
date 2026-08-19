param(
  [Parameter(Mandatory = $true)][string]$RepoRoot,
  [Parameter(Mandatory = $true)][string]$RuntimeRoot,
  [Parameter(Mandatory = $true)][string]$X1ModelRoot,
  [string]$PythonExe = "python",
  [int]$BatchSize = 100
)

$ErrorActionPreference = "Stop"
$resolvedRepo = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedRuntime = [IO.Path]::GetFullPath($RuntimeRoot)
$resolvedModel = (Resolve-Path -LiteralPath $X1ModelRoot).Path
$src = Join-Path $resolvedRepo "src"
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($previousPythonPath) { "$src;$previousPythonPath" } else { $src }
$env:PYTHONUNBUFFERED = "1"

& $PythonExe -m idx_trade.v4_x1_eod_legacy_compat `
  --runtime-root $resolvedRuntime `
  --x1-model-root $resolvedModel `
  --repo-root $resolvedRepo `
  --batch-size $BatchSize

exit $LASTEXITCODE

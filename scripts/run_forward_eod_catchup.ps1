param(
  [Parameter(Mandatory = $true)][string]$RepoRoot,
  [Parameter(Mandatory = $true)][string]$RuntimeRoot,
  [string]$PythonExe = "python",
  [int]$BatchSize = 100
)

$ErrorActionPreference = "Stop"
$resolvedRepo = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedRuntime = [IO.Path]::GetFullPath($RuntimeRoot)
$src = Join-Path $resolvedRepo "src"
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($previousPythonPath) { "$src;$previousPythonPath" } else { $src }
$env:PYTHONUNBUFFERED = "1"

& $PythonExe -m idx_trade.forward_eod_runner `
  --runtime-root $resolvedRuntime `
  --batch-size $BatchSize
exit $LASTEXITCODE

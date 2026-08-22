param(
  [Parameter(Mandatory = $true)][string]$RepoRoot,
  [Parameter(Mandatory = $true)][string]$RuntimeRoot,
  [string]$PythonExe = "python",
  [double]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$resolvedRepo = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedRuntime = [IO.Path]::GetFullPath($RuntimeRoot)
$src = Join-Path $resolvedRepo "src"
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($previousPythonPath) { "$src;$previousPythonPath" } else { $src }
$env:PYTHONUNBUFFERED = "1"

$logRoot = Join-Path $resolvedRuntime "official_open\logs"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logRoot "official-open-$stamp.log"

& $PythonExe -m idx_trade.official_open_capture_runtime_v1 `
  --runtime-root $resolvedRuntime `
  --timeout-seconds $TimeoutSeconds *>&1 | Tee-Object -FilePath $logPath
exit $LASTEXITCODE

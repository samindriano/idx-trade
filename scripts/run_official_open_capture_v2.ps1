param(
  [Parameter(Mandatory = $true)][string]$RepoRoot,
  [Parameter(Mandatory = $true)][string]$RuntimeRoot,
  [string]$ExecutionScheduleAttestation,
  [string]$ExecutionScheduleAttestationSha256,
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
$logPath = Join-Path $logRoot "official-open-v2-$stamp.log"

$args = @(
  "-m", "idx_trade.official_open_capture_runtime_v2",
  "--runtime-root", $resolvedRuntime,
  "--timeout-seconds", $TimeoutSeconds
)
if ($ExecutionScheduleAttestation) {
  if (-not $ExecutionScheduleAttestationSha256) {
    throw "ExecutionScheduleAttestationSha256 is required when ExecutionScheduleAttestation is supplied."
  }
  $args += @(
    "--execution-schedule-attestation", $ExecutionScheduleAttestation,
    "--execution-schedule-attestation-sha256", $ExecutionScheduleAttestationSha256
  )
}

& $PythonExe @args *>&1 | Tee-Object -FilePath $logPath
exit $LASTEXITCODE

param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Branch = "research/idx-v4-x1-clean-historical-oos-replay-v1"
$ProjectRoot = "D:\Documents\Project"
$DataGateRoot = "D:\Documents\Project\idx-trade-data-gate-20260808v"
$PhaseARoot = "D:\Documents\Project\idx-v4-x1-clean-phase-a-open-lineage-remediation-20260820-v1"
$ExecutionLockManifest = "D:\Documents\Project\idx-v4-x1-clean-phase-a-execution-lock-20260820-v1\v4_x1_clean_phase_a_execution_lock_manifest.json"
$StageARoot = Join-Path $DataGateRoot "v4_x_clean_data_consolidation_v1_20260820"
$StageBRoot = Join-Path $DataGateRoot "v4_x_clean_data_consolidation_v1_stage_b_final_20260820"
$OutputDir = "D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v1"

$Expected = @{
  execution_lock = "1846c94a74de8132672777c96f46580d298f942d87584e12b5e99e78e83a77f3"
  clean_bundle = "561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358"
  clean_panel = "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e"
  clean_master = "51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e"
  field_provenance = "cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28"
  parent_combined_manifest = "12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43"
  old_open_derivative = "a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab"
  old_open_overlay = "2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41"
}

$ScriptPath = $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path (Split-Path -Parent $ScriptPath) "..")).Path

function Sha256([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Resolve-ByHash {
  param(
    [Parameter(Mandatory=$true)][string[]]$Roots,
    [Parameter(Mandatory=$true)][string]$ExpectedSha,
    [string]$Filter = "*"
  )
  $hits = New-Object System.Collections.Generic.List[string]
  foreach ($root in $Roots) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    Get-ChildItem -LiteralPath $root -Recurse -File -Filter $Filter -ErrorAction SilentlyContinue | ForEach-Object {
      try {
        if ((Sha256 $_.FullName) -eq $ExpectedSha.ToLowerInvariant()) {
          $hits.Add($_.FullName)
        }
      } catch {}
    }
  }
  if ($hits.Count -lt 1) { throw "HASH_NOT_FOUND:${ExpectedSha}:$($Roots -join ';')" }
  return ($hits | Sort-Object -Unique | Select-Object -First 1)
}

$branchNow = (& git -C $RepoRoot branch --show-current).Trim()
if ($branchNow -ne $Branch) { throw "WRONG_BRANCH:$branchNow" }
if ((& git -C $RepoRoot status --porcelain)) { throw "WORKTREE_NOT_CLEAN" }
if (Test-Path -LiteralPath $OutputDir) { throw "OUTPUT_ALREADY_EXISTS:$OutputDir" }
if (-not (Test-Path -LiteralPath $PhaseARoot -PathType Container)) { throw "PHASE_A_ROOT_MISSING" }
if (-not (Test-Path -LiteralPath $ExecutionLockManifest -PathType Leaf)) { throw "EXECUTION_LOCK_MISSING" }
if ((Sha256 $ExecutionLockManifest) -ne $Expected.execution_lock) { throw "EXECUTION_LOCK_SHA_MISMATCH" }

$runnerBlob = (& git -C $RepoRoot rev-parse "HEAD:scripts/run_v4_x1_clean_historical_oos_replay.py").Trim()
$configBlob = (& git -C $RepoRoot rev-parse "HEAD:config/ranking_v4_x1_clean_historical_oos_replay_v1.json").Trim()
if ($runnerBlob -ne "273ec17f8d2da0d23ac5d2e9f08661b6ff6a35d7") { throw "RUNNER_BLOB_CHANGED:$runnerBlob" }
if ($configBlob -ne "583fe1791e0f2534032a41713e56a18f6d968e80") { throw "CONFIG_BLOB_CHANGED:$configBlob" }

Write-Host "Resolving frozen local inputs by SHA..."
$CleanPanel = Resolve-ByHash -Roots @($StageARoot) -ExpectedSha $Expected.clean_panel -Filter "*.parquet"
$CleanMaster = Resolve-ByHash -Roots @($StageBRoot) -ExpectedSha $Expected.clean_master -Filter "*.csv"
$CleanBundle = Resolve-ByHash -Roots @($StageARoot, $StageBRoot) -ExpectedSha $Expected.clean_bundle -Filter "*.json"
$FieldProvenance = Resolve-ByHash -Roots @($StageARoot, $StageBRoot) -ExpectedSha $Expected.field_provenance -Filter "*.parquet"
$ParentCombinedManifest = Resolve-ByHash -Roots @($ProjectRoot) -ExpectedSha $Expected.parent_combined_manifest -Filter "MANIFEST.json"
$ParentCombinedRoot = Split-Path -Parent $ParentCombinedManifest
$OpenDerivative = Resolve-ByHash -Roots @($ProjectRoot) -ExpectedSha $Expected.old_open_derivative -Filter "execution_open_candidate_panel_yahoo_tradingview.parquet"
$OpenDerivativeRoot = Split-Path -Parent $OpenDerivative
$OpenOverlay = Resolve-ByHash -Roots @($ProjectRoot) -ExpectedSha $Expected.old_open_overlay -Filter "open_recovery_overlay.parquet"
$OverlayRoot = Split-Path -Parent $OpenOverlay

$resolved = [ordered]@{
  clean_panel = $CleanPanel
  clean_security_master = $CleanMaster
  clean_bundle_manifest = $CleanBundle
  field_provenance = $FieldProvenance
  parent_combined_replay_root = $ParentCombinedRoot
  open_derivative_root = $OpenDerivativeRoot
  overlay_root = $OverlayRoot
  phase_a_root = $PhaseARoot
  execution_lock_manifest = $ExecutionLockManifest
  artifact_root = $DataGateRoot
  output_dir = $OutputDir
}
Write-Host ($resolved | ConvertTo-Json -Depth 4)

$runner = Join-Path $RepoRoot "scripts\run_v4_x1_clean_historical_oos_replay.py"
$env:PYTHONPATH = (Join-Path $RepoRoot "src")

Write-Host "`nRunning exactly one locked 24-fit clean historical OOS replay..."
& python $runner `
  --phase-a-root $PhaseARoot `
  --execution-lock-manifest $ExecutionLockManifest `
  --clean-bundle-manifest $CleanBundle `
  --clean-panel $CleanPanel `
  --clean-security-master $CleanMaster `
  --field-provenance $FieldProvenance `
  --parent-combined-replay-root $ParentCombinedRoot `
  --artifact-root $DataGateRoot `
  --open-derivative-root $OpenDerivativeRoot `
  --overlay-root $OverlayRoot `
  --output-dir $OutputDir `
  --repo-root $RepoRoot

if ($LASTEXITCODE -ne 0) { throw "CLEAN_HISTORICAL_OOS_REPLAY_FAILED:$LASTEXITCODE" }

$summaryPath = Join-Path $OutputDir "summary.json"
$manifestPath = Join-Path $OutputDir "MANIFEST.json"
if (-not (Test-Path -LiteralPath $summaryPath)) { throw "SUMMARY_MISSING_AFTER_RUN" }
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "MANIFEST_MISSING_AFTER_RUN" }
$summary = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json

Write-Host "`n=== CLEAN HISTORICAL OOS RESULT ==="
Write-Host ("Parent pre-clean IC : {0:N6}" -f [double]$summary.parent_preclean_historical_oos_ic)
Write-Host ("Clean historical IC : {0:N6}" -f [double]$summary.canonical_clean_historical_oos_ic)
Write-Host ("Absolute delta       : {0:+0.000000;-0.000000;0.000000}" -f [double]$summary.absolute_delta_vs_parent)
Write-Host ("Relative delta       : {0:+0.00%;-0.00%;0.00%}" -f [double]$summary.relative_delta_vs_parent)
Write-Host ("Control clean IC     : {0:N6}" -f [double]$summary.control_clean_consensus_ic)
Write-Host ("Fit count            : {0}" -f [int]$summary.fit_count)
Write-Host ("Manifest SHA256      : {0}" -f (Sha256 $manifestPath))
Write-Host "Forward counter/model were not touched by this runner."

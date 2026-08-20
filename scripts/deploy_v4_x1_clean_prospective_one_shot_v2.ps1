param(
  [switch]$Elevated
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$TaskName = "IDXTrade-ForwardEOD"
$Branch = "integration/v4-x1-clean-prospective-score-v1"
$RuntimeRoot = "D:\Documents\Project\idx-trade-data-gate-20260808v"
$ModelRoot = "D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1"
$OldModelRoot = "D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1"
$StageARoot = "D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_20260820"
$StageBRoot = "D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_stage_b_final_20260820"
$ObservedBy = "2026-08-20T12:08:44+00:00"
$ExpectedModelManifest = "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf"
$ExpectedPanel = "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e"
$ExpectedMaster = "51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e"
$EvidenceRoot = "D:\Documents\Project\idx-v4-x1-clean-prospective-deployment-privilege-retry-20260820-v1"

$ScriptPath = $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path (Split-Path -Parent $ScriptPath) "..")).Path

function Test-IsAdministrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
  Write-Host "Requesting Administrator privilege via UAC..."
  $args = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"' + $ScriptPath + '"'),
    "-Elevated"
  )
  $child = Start-Process -FilePath "powershell.exe" -ArgumentList $args -Verb RunAs -Wait -PassThru
  $summaryPath = Join-Path $EvidenceRoot "deployment_summary.json"
  if (Test-Path -LiteralPath $summaryPath -PathType Leaf) {
    Write-Host "`nDEPLOYMENT RESULT"
    Get-Content -LiteralPath $summaryPath -Raw
  } else {
    Write-Host "Elevated deployment process exited with code $($child.ExitCode). No deployment summary was produced."
  }
  exit $child.ExitCode
}

if (-not $Elevated) { throw "SELF_ELEVATION_STATE_INVALID" }

function Get-Sha256([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Resolve-UniqueOrIdenticalHash {
  param(
    [Parameter(Mandatory=$true)][string]$Root,
    [Parameter(Mandatory=$true)][string]$ExpectedSha,
    [string]$Filter = "*"
  )
  $hits = @(
    Get-ChildItem -LiteralPath $Root -Recurse -File -Filter $Filter -ErrorAction SilentlyContinue |
      Where-Object { (Get-Sha256 $_.FullName) -eq $ExpectedSha.ToLowerInvariant() } |
      Sort-Object FullName
  )
  if ($hits.Count -lt 1) { throw "HASH_NOT_FOUND:${ExpectedSha}:${Root}" }
  return $hits[0].FullName
}

function Git-Blob([string]$Path) {
  $value = (& git -C $RepoRoot rev-parse "HEAD:$Path" 2>$null)
  if ($LASTEXITCODE -ne 0) { throw "GIT_BLOB_RESOLVE_FAILED:$Path" }
  return $value.Trim()
}

function Assert-Contains([string]$Haystack, [string]$Needle, [string]$Label) {
  if ($Haystack -notlike "*$Needle*") { throw "MISSING_${Label}:$Needle" }
}

$branchNow = (& git -C $RepoRoot branch --show-current).Trim()
if ($branchNow -ne $Branch) { throw "WRONG_BRANCH:$branchNow" }
if ((& git -C $RepoRoot status --porcelain)) { throw "WORKTREE_NOT_CLEAN" }

$requiredBlobs = @{
  "scripts/update_forward_eod_task_v4_x1_clean.ps1" = "7b06fa4914c090a5aa76f767347de71bd9dd95a1"
  "scripts/run_forward_eod_v4_x1_clean_pipeline.ps1" = "5b3c3939ae87ce666bb9b1cd02ae4689d743122d"
  "scripts/run_v4_x1_clean_forward_readiness.py" = "07c38a0e27a0acfb7f5af49a7ea9b8b8fb822e1d"
  "src/idx_trade/v4_x1_clean_forward_score.py" = "f00528422a42835e5a969bfe503e29f91e0bf957"
  "config/ranking_v4_x1_clean_prospective_deployment_v1.json" = "7919b21f3bf5451cc68687ee2fc2cf25b341fca2"
  "config/ranking_v4_x1_clean_prospective_deployment_privilege_retry_v1.json" = "bf9ca2bdc9a1c7f7ab60a1fa3984f3f508c6196a"
}
foreach ($entry in $requiredBlobs.GetEnumerator()) {
  $actual = Git-Blob $entry.Key
  if ($actual -ne $entry.Value) { throw "FROZEN_BLOB_MISMATCH:$($entry.Key):$actual" }
}

if (-not (Test-Path -LiteralPath $RuntimeRoot -PathType Container)) { throw "RUNTIME_ROOT_MISSING" }
if (-not (Test-Path -LiteralPath $ModelRoot -PathType Container)) { throw "MODEL_ROOT_MISSING" }
$modelManifestPath = Join-Path $ModelRoot "MANIFEST.json"
if ((Get-Sha256 $modelManifestPath) -ne $ExpectedModelManifest) { throw "MODEL_MANIFEST_SHA_MISMATCH" }

$CleanPanel = Resolve-UniqueOrIdenticalHash -Root $StageARoot -ExpectedSha $ExpectedPanel -Filter "*.parquet"
$CleanMaster = Resolve-UniqueOrIdenticalHash -Root $StageBRoot -ExpectedSha $ExpectedMaster -Filter "*"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if ($task.State -ne "Ready") { throw "TASK_NOT_READY:$($task.State)" }
$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
$preLastRun = $taskInfo.LastRunTime
$preAction = $task.Actions | Select-Object -First 1
Assert-Contains $preAction.Arguments $OldModelRoot "OLD_MODEL_ROOT_PRECONDITION"
if ($preAction.Arguments -like "*run_forward_eod_v4_x1_clean_pipeline.ps1*") { throw "TASK_ALREADY_POINTS_TO_CLEAN_PIPELINE" }

if (Test-Path -LiteralPath $EvidenceRoot) { throw "EVIDENCE_ROOT_ALREADY_EXISTS:$EvidenceRoot" }
New-Item -ItemType Directory -Path $EvidenceRoot | Out-Null
$preXml = Export-ScheduledTask -TaskName $TaskName
$preXmlPath = Join-Path $EvidenceRoot "task_pre.xml"
Set-Content -LiteralPath $preXmlPath -Value $preXml -Encoding UTF8

$readinessScript = Join-Path $RepoRoot "scripts\run_v4_x1_clean_forward_readiness.py"
$readinessArgs = @(
  $readinessScript,
  "--runtime-root", $RuntimeRoot,
  "--x1-model-root", $ModelRoot,
  "--clean-panel", $CleanPanel,
  "--clean-security-master", $CleanMaster,
  "--observed-by", $ObservedBy
)
$preReadinessText = (& python @readinessArgs | Out-String)
if ($LASTEXITCODE -ne 0) { throw "PRE_READINESS_FAILED" }
$preReadiness = $preReadinessText | ConvertFrom-Json
if ([int]$preReadiness.counter_completed -ne 0) { throw "PRE_COUNTER_NOT_ZERO:$($preReadiness.counter_completed)" }
Set-Content -LiteralPath (Join-Path $EvidenceRoot "readiness_pre.json") -Value $preReadinessText -Encoding UTF8

$updater = Join-Path $RepoRoot "scripts\update_forward_eod_task_v4_x1_clean.ps1"
& $updater `
  -RepoRoot $RepoRoot `
  -RuntimeRoot $RuntimeRoot `
  -X1ModelRoot $ModelRoot `
  -CleanPanel $CleanPanel `
  -CleanSecurityMaster $CleanMaster `
  -PythonExe "python" `
  -TaskName $TaskName `
  -ObservedBy $ObservedBy
if ($LASTEXITCODE -ne 0) { throw "UPDATER_FAILED:$LASTEXITCODE" }

$postTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if ($postTask.State -ne "Ready") { throw "POST_TASK_NOT_READY:$($postTask.State)" }
$postInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
if ($postInfo.LastRunTime -ne $preLastRun) { throw "LAST_RUN_TIME_CHANGED_DURING_DEPLOYMENT:$preLastRun->$($postInfo.LastRunTime)" }
$postAction = $postTask.Actions | Select-Object -First 1
Assert-Contains $postAction.Arguments "run_forward_eod_v4_x1_clean_pipeline.ps1" "CLEAN_PIPELINE"
Assert-Contains $postAction.Arguments $ModelRoot "CLEAN_MODEL_ROOT"
Assert-Contains $postAction.Arguments $CleanPanel "CLEAN_PANEL"
Assert-Contains $postAction.Arguments $CleanMaster "CLEAN_SECURITY_MASTER"
Assert-Contains $postAction.Arguments $ObservedBy "FREEZE_BOUNDARY"

$dailyTimes = @($postTask.Triggers | Where-Object { $_.StartBoundary } | ForEach-Object { ([datetime]$_.StartBoundary).ToString("HH:mm") })
foreach ($time in @("18:30", "19:30", "20:30")) {
  if ($time -notin $dailyTimes) { throw "POST_TRIGGER_MISSING:$time" }
}
$hasLogon = @($postTask.Triggers | Where-Object { $_.CimClass.CimClassName -eq "MSFT_TaskLogonTrigger" }).Count -gt 0
if (-not $hasLogon) { throw "POST_AT_LOGON_TRIGGER_MISSING" }

$postXml = Export-ScheduledTask -TaskName $TaskName
$postXmlPath = Join-Path $EvidenceRoot "task_post.xml"
Set-Content -LiteralPath $postXmlPath -Value $postXml -Encoding UTF8

$postReadinessText = (& python @readinessArgs | Out-String)
if ($LASTEXITCODE -ne 0) { throw "POST_READINESS_FAILED" }
$postReadiness = $postReadinessText | ConvertFrom-Json
if ([int]$postReadiness.counter_completed -ne 0) { throw "POST_COUNTER_NOT_ZERO:$($postReadiness.counter_completed)" }
Set-Content -LiteralPath (Join-Path $EvidenceRoot "readiness_post.json") -Value $postReadinessText -Encoding UTF8

$summary = [ordered]@{
  status = "V4_X1_CLEAN_PROSPECTIVE_DEPLOYMENT_COMPLETE_VERIFY_ONLY"
  administrator = $true
  branch = $branchNow
  head = (& git -C $RepoRoot rev-parse HEAD).Trim()
  task_name = $TaskName
  task_state = [string]$postTask.State
  last_run_time_pre = $preLastRun.ToString("o")
  last_run_time_post = $postInfo.LastRunTime.ToString("o")
  last_run_time_unchanged = ($postInfo.LastRunTime -eq $preLastRun)
  pre_task_xml_sha256 = Get-Sha256 $preXmlPath
  post_task_xml_sha256 = Get-Sha256 $postXmlPath
  runtime_root = $RuntimeRoot
  clean_model_root = $ModelRoot
  clean_panel = $CleanPanel
  clean_panel_sha256 = Get-Sha256 $CleanPanel
  clean_security_master = $CleanMaster
  clean_security_master_sha256 = Get-Sha256 $CleanMaster
  model_manifest_sha256 = Get-Sha256 $modelManifestPath
  freeze_boundary = $ObservedBy
  counter_pre = [int]$preReadiness.counter_completed
  counter_post = [int]$postReadiness.counter_completed
  readiness_post_status = [string]$postReadiness.status
  scheduled_task_mutated = $true
  manual_task_start = $false
  manual_pipeline_run = $false
  score_capture_performed = $false
  outcome_accessed = $false
  evidence_root = $EvidenceRoot
}
$summaryJson = $summary | ConvertTo-Json -Depth 6
Set-Content -LiteralPath (Join-Path $EvidenceRoot "deployment_summary.json") -Value $summaryJson -Encoding UTF8
Write-Host "`nDEPLOYMENT_PASS"
Write-Output $summaryJson

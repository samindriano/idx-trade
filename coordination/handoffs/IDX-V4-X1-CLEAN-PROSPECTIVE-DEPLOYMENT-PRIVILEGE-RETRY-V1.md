# Handoff — V4-X1 Clean Prospective Deployment Privilege Retry V1

Branch: `integration/v4-x1-clean-prospective-score-v1`  
Scope: exactly one Administrator-privileged scheduled-task migration retry, then read-only verification. **No manual pipeline run and no manual scoring.**

## Authorization

Controlling checkpoint:

- `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_DEPLOYMENT_PRIVILEGE_RETRY_AUTHORIZED.md`
- blob `e7cb00a3da5618283f681bd6364b42515c205298`
- decision `V4_X1_CLEAN_PROSPECTIVE_DEPLOYMENT_PRIVILEGE_RETRY_AUTHORIZED`

Retry contract:

- `config/ranking_v4_x1_clean_prospective_deployment_privilege_retry_v1.json`
- blob `bf9ca2bdc9a1c7f7ab60a1fa3984f3f508c6196a`
- exactly one retry attempt authorized
- Administrator process required before updater invocation

Parent deployment contract remains:

- `config/ranking_v4_x1_clean_prospective_deployment_v1.json`
- blob `7919b21f3bf5451cc68687ee2fc2cf25b341fca2`

The first Deployment V1 attempt exited before `Set-ScheduledTask`; `scheduled_task_mutated=false`. Its no-retry rule is not reused here; this is a new independent privilege-only handoff.

## Before any local mutation

1. Fetch/read latest `origin/main:coordination/TEAM_STATUS.md`.
2. Confirm no duplicate `ACTIVE` owner for clean prospective deployment.
3. Change only this canonical lane from `REVIEW` to `ACTIVE`, preserving every other row.
4. Checkout/fetch this branch and fast-forward to remote.
5. Worktree must be clean.
6. Verify current process is elevated Administrator **before** invoking the updater.

Administrator check:

```powershell
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Host "Administrator=$isAdmin"
if (-not $isAdmin) { throw "STOP_NOT_ADMINISTRATOR" }
```

If this fails, STOP before updater invocation. Do not consume the authorized retry. The user must reopen PowerShell/terminal with **Run as administrator** and restart this handoff from preflight.

## Exact frozen Git identities

Verify:

```powershell
git rev-parse HEAD:config/ranking_v4_x1_clean_prospective_deployment_v1.json
git rev-parse HEAD:config/ranking_v4_x1_clean_prospective_deployment_privilege_retry_v1.json
git rev-parse HEAD:docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_DEPLOYMENT_PRIVILEGE_RETRY_AUTHORIZED.md
git rev-parse HEAD:scripts/update_forward_eod_task_v4_x1_clean.ps1
git rev-parse HEAD:scripts/run_forward_eod_v4_x1_clean_pipeline.ps1
git rev-parse HEAD:scripts/run_v4_x1_clean_forward_readiness.py
```

Expected respectively:

- `7919b21f3bf5451cc68687ee2fc2cf25b341fca2`
- `bf9ca2bdc9a1c7f7ab60a1fa3984f3f508c6196a`
- `e7cb00a3da5618283f681bd6364b42515c205298`
- `7b06fa4914c090a5aa76f767347de71bd9dd95a1`
- `5b3c3939ae87ce666bb9b1cd02ae4689d743122d`
- `07c38a0e27a0acfb7f5af49a7ea9b8b8fb822e1d`

Any mismatch => STOP.

## Accepted external inputs

Canonical runtime root:

`D:\Documents\Project\idx-trade-data-gate-20260808v`

Clean model root:

`D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1`

Required model manifest SHA-256:

`30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`

Accepted clean panel SHA-256:

`25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`

Accepted clean security-master SHA-256:

`51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`

Resolve panel and security-master exact paths by SHA-256 under their already accepted Stage-A/Stage-B roots if necessary. Multiple byte-identical copies are acceptable; choose deterministically and report the selected path.

## Pre-retry read-only verification

Before mutation:

1. Read task `IDXTrade-ForwardEOD`.
2. Require `State=Ready`.
3. Require current action still references old model root:
   `D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1`.
4. Require current action has **not** already been migrated to `run_forward_eod_v4_x1_clean_pipeline.ps1`.
5. Record current `LastRunTime`, action, triggers, working directory.
6. Export task XML and SHA-256 it into a new retry evidence root, e.g.
   `D:\Documents\Project\idx-v4-x1-clean-prospective-deployment-privilege-retry-20260820-v1`.
7. Run clean readiness read-only once and require counter `0/100`.

Readiness command:

```powershell
python scripts/run_v4_x1_clean_forward_readiness.py `
  --runtime-root "D:\Documents\Project\idx-trade-data-gate-20260808v" `
  --x1-model-root "D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1" `
  --clean-panel "<EXACT_CLEAN_PANEL_PATH>" `
  --clean-security-master "<EXACT_CLEAN_SECURITY_MASTER_PATH>" `
  --observed-by "2026-08-20T12:08:44+00:00"
```

Required before updater:

- counter completed `0`;
- no score capture;
- no registry mutation;
- no outcome access.

A readiness candidate, if any, still does **not** authorize manual scoring during deployment.

## Exactly one Administrator updater invocation

Only after every precondition above passes, invoke exactly once:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/update_forward_eod_task_v4_x1_clean.ps1 `
  -RepoRoot "<EXACT_REPO_ROOT>" `
  -RuntimeRoot "D:\Documents\Project\idx-trade-data-gate-20260808v" `
  -X1ModelRoot "D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1" `
  -CleanPanel "<EXACT_CLEAN_PANEL_PATH>" `
  -CleanSecurityMaster "<EXACT_CLEAN_SECURITY_MASTER_PATH>" `
  -PythonExe "<EXACT_PYTHON_EXE>" `
  -TaskName "IDXTrade-ForwardEOD" `
  -ObservedBy "2026-08-20T12:08:44+00:00"
```

Do not invoke the updater a second time if it fails.

## Post-retry read-only verification

Immediately after updater PASS:

- require task `State=Ready`;
- require action references `run_forward_eod_v4_x1_clean_pipeline.ps1`;
- require clean model root, clean panel, clean security master, canonical runtime root, Python executable, and observed-by boundary in action arguments;
- require daily triggers exactly `18:30`, `19:30`, `20:30` plus AtLogOn;
- require `LastRunTime` unchanged from the pre-retry snapshot;
- export post-task XML and SHA-256 it;
- run the clean readiness script read-only again;
- require clean counter still `0/100` immediately after migration;
- require `score_capture_performed=false` during deployment.

Do **not** call `Start-ScheduledTask`. Do **not** run the clean EOD pipeline or score CLI manually.

## Failure policy

- If Administrator precheck fails: STOP before updater; retry remains unconsumed.
- If any other precondition fails: STOP before mutation.
- If the single updater invocation fails: STOP; no further retry in this handoff.
- If post-verification fails: STOP; do not run pipeline manually.
- Do not patch scorer/pipeline/updater/config under this handoff.

## Required report

Return:

- branch + HEAD + clean/synced state;
- canonical TEAM_STATUS ACTIVE and REVIEW commits;
- Administrator precheck PASS;
- frozen blob verification 6/6;
- exact selected model/panel/security-master paths and SHA verification;
- pre task State, LastRunTime, action, triggers, XML SHA;
- pre readiness status + counter;
- updater invocation count exactly 1 and result;
- post task State, LastRunTime, action, triggers, XML SHA;
- confirmation LastRunTime unchanged during migration;
- post readiness status + counter;
- `scheduled_task_mutated=true` only if updater PASS;
- `manual_task_start=false`;
- `manual_pipeline_run=false`;
- `score_capture_performed=false`;
- `outcome_accessed=false`.

Update only this deployment lane in canonical TEAM_STATUS to `REVIEW`, then STOP.

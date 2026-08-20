# Handoff — V4-X1 Clean Prospective Deployment V1

Branch: `integration/v4-x1-clean-prospective-score-v1`  
Scope: **exactly one existing-task migration + read-only verification. No manual pipeline/score run.**

## Authorization

Controlling acceptance:

- `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_READINESS_ACCEPTED_DEPLOYMENT_AUTHORIZED.md`
- blob `a18621a03cdd9168e6b9cd0e625144e3eb3bb2c1`
- verdict `V4_X1_CLEAN_PROSPECTIVE_READINESS_ACCEPTED_DEPLOYMENT_ONLY_AUTHORIZED`

Deployment contract:

- `config/ranking_v4_x1_clean_prospective_deployment_v1.json`
- blob `7919b21f3bf5451cc68687ee2fc2cf25b341fca2`

Deployment claim:

- `coordination/claims/IDX-V4-X1-CLEAN-PROSPECTIVE-DEPLOYMENT-V1.md`

## Timing hard gate

Do not start scheduler mutation before:

`2026-08-20 20:35:00 Asia/Jakarta`

This deliberately lets the pre-existing 20:30 trigger finish under the old task definition before migration.

At deployment time, the existing task must be `Ready`. If it is `Running`, wait for it to finish; do not stop it. If it is not `Ready` afterward, STOP for review.

## Before mutation

1. Fetch/read latest `origin/main:coordination/TEAM_STATUS.md`.
2. Confirm no duplicate ACTIVE clean prospective deployment lane.
3. Update only the relevant canonical clean prospective lane to ACTIVE, preserving all other rows.
4. Fetch/checkout this branch and fast-forward.
5. Worktree must be clean.
6. Verify current local Jakarta time is >= 20:35.
7. Verify exact blobs:
   - deployment config `7919b21f3bf5451cc68687ee2fc2cf25b341fca2`
   - deployment acceptance checkpoint `a18621a03cdd9168e6b9cd0e625144e3eb3bb2c1`
   - clean task updater `7b06fa4914c090a5aa76f767347de71bd9dd95a1`
   - clean pipeline PowerShell `5b3c3939ae87ce666bb9b1cd02ae4689d743122d`
   - clean score adapter `f00528422a42835e5a969bfe503e29f91e0bf957`
   - clean EOD adapter `2ce4fbcb9baec5c39ced4fadaaf58dc4d73a6216`
8. Verify accepted external hashes before mutation:
   - model manifest `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`
   - clean panel `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
   - clean security master `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`

Use the same exact panel/master paths selected in accepted R2 if available. If resolving by hash again, multiple byte-identical copies are allowed; select deterministically and report the path.

## Existing task precondition

Task name:

`IDXTrade-ForwardEOD`

Must verify before mutation:

- State = `Ready`;
- Runtime root = `D:\Documents\Project\idx-trade-data-gate-20260808v`;
- current model root still = `D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1`;
- triggers daily 18:30, 19:30, 20:30 plus AtLogOn;
- current task action is still the prior V4-X1 pipeline, not already clean.

If any precondition differs, STOP before mutation.

## Evidence root

Create a new local evidence directory, for example:

`D:\Documents\Project\idx-v4-x1-clean-prospective-deployment-20260820-v1`

Before mutation save:

- `pre_task.xml` from `Export-ScheduledTask`;
- a JSON/text snapshot containing State, LastRunTime, LastTaskResult, action, WorkingDirectory, triggers;
- SHA-256 of `pre_task.xml`.

Record `LastRunTime` as `PRE_LAST_RUN_TIME`.

Do not modify the task while collecting this evidence.

## Exactly one authorized mutation

Use only:

`scripts/update_forward_eod_task_v4_x1_clean.ps1`

Invoke it exactly once from **Administrator PowerShell** with:

- repo root = current checked-out repo;
- runtime root = `D:\Documents\Project\idx-trade-data-gate-20260808v`;
- model root = `D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1`;
- exact accepted clean panel path;
- exact accepted clean security-master path;
- observed-by = `2026-08-20T12:08:44+00:00`;
- TaskName = `IDXTrade-ForwardEOD`.

Do not call `Set-ScheduledTask` separately and do not rerun the updater.

If updater exits nonzero or verification inside it fails: STOP immediately. Do not retry, do not run the pipeline, do not score.

## Post-mutation read-only verification

Immediately inspect the task without starting it.

Required:

- State = `Ready`;
- action script = `scripts/run_forward_eod_v4_x1_clean_pipeline.ps1`;
- action args contain canonical runtime root;
- action args contain accepted clean model root;
- action args contain exact clean panel path;
- action args contain exact clean security-master path;
- action args contain `2026-08-20T12:08:44+00:00`;
- WorkingDirectory is the repo root;
- daily triggers still exactly 18:30, 19:30, 20:30;
- AtLogOn still exists;
- `LastRunTime` equals `PRE_LAST_RUN_TIME` (proves task was not run during migration).

Save:

- `post_task.xml`;
- post-task snapshot;
- SHA-256 of `post_task.xml`.

If post verification fails: STOP. Do not start the task or manually run the pipeline.

## Immediate read-only readiness recheck

After successful task verification, run only the existing read-only readiness script:

```powershell
python scripts/run_v4_x1_clean_forward_readiness.py `
  --runtime-root "D:\Documents\Project\idx-trade-data-gate-20260808v" `
  --x1-model-root "D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1" `
  --clean-panel "<EXACT_CLEAN_PANEL_PATH>" `
  --clean-security-master "<EXACT_CLEAN_SECURITY_MASTER_PATH>" `
  --observed-by "2026-08-20T12:08:44+00:00"
```

Expected immediately after deployment:

- clean counter still `0/100`;
- score capture performed = false;
- registry mutation = false;
- provider/network = false;
- outcome access = false.

A candidate, if somehow reported, still does not authorize a manual score in this handoff.

## After successful deployment

Do **not** manually start `IDXTrade-ForwardEOD`.

Leave the task `Ready` and let its next normal trigger drive canonical EOD + clean score under the frozen same-day prospective rules.

Automatic future scoring is authorized only when runtime evidence satisfies all freshness gates. There is no retroactive credit for 2026-08-20 or any late catch-up session.

## Explicit prohibitions

- no manual EOD pipeline run;
- no direct score CLI;
- no manual scheduled-task start;
- no second task/runtime/registry/provider path;
- no counter edits;
- no old V4-X1 counter reuse;
- no outcome access;
- no model fit/retune;
- no historical/backfill scoring;
- no feature/session/CA80/security-master policy changes;
- no V4-X2 semantics.

## Required report

Return:

- branch + HEAD, clean/synced;
- canonical TEAM_STATUS ACTIVE/REVIEW commits;
- deployment start time Jakarta and confirmation >= 20:35;
- exact blob/hash verification;
- exact chosen panel/master/model paths;
- pre-task State, LastRunTime, action, triggers, XML SHA;
- updater result (`TASK_UPDATE_PASS` or failure);
- post-task State, LastRunTime, action, triggers, XML SHA;
- whether LastRunTime stayed unchanged during migration;
- post-deployment readiness status;
- clean counter completed/target/remaining/sessions;
- candidate if any;
- history gaps/ignored backfills if any;
- all safety flags;
- `scheduled_task_mutated` true only if updater succeeded;
- `manual_task_start=false`;
- `manual_pipeline_run=false`;
- `score_capture_performed=false`;
- `outcome_accessed=false`.

Update only this deployment lane to REVIEW, then STOP for independent verification of deployment evidence.

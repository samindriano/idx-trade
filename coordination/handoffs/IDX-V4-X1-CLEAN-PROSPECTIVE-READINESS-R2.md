# Handoff — V4-X1 Clean Prospective Read-Only Readiness R2

Branch: `integration/v4-x1-clean-prospective-score-v1`  
Scope: validation + read-only readiness only. **No deployment and no score capture.**

This R2 supersedes `coordination/handoffs/IDX-V4-X1-CLEAN-PROSPECTIVE-READINESS.md` only because the original substring-based static guard produced a false positive.

## Authorization

Preparation parent:

- `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_SCORE_PREPARED.md`
- blob `690e5eb2a3e903b2e1165523c2c363b8bfbfd5ec`
- decision `V4_X1_CLEAN_PROSPECTIVE_SCORE_PREPARED_READONLY_LOCAL_READINESS_AUTHORIZED`

Controlling remediation checkpoint:

- `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_STATIC_GUARD_REMEDIATED.md`
- blob `177b95214c49f0c44748389aaef5ef20d3881267`
- decision `V4_X1_CLEAN_PROSPECTIVE_STATIC_GUARD_REMEDIATED_READONLY_PREFLIGHT_RETRY_AUTHORIZED`

Machine contract:

- `config/ranking_v4_x1_clean_prospective_score_v1.json`
- blob `fbdbed664259cf685a71dbbfebcc38ba7e558c92`
- `deployment_authorized=false`
- `score_capture_authorized=false`
- expected clean counter before deployment `0/100`

The clean scorer itself was **not changed** by remediation; only the static test and its config pin changed.

## Before local work

1. Fetch/read latest `origin/main:coordination/TEAM_STATUS.md`.
2. Confirm no duplicate `ACTIVE` owner for this clean prospective readiness scope.
3. Change only this canonical lane from `REVIEW` to `ACTIVE` for the R2 pass, preserving every other row.
4. Checkout/fetch this branch and fast-forward to remote.
5. Worktree must be clean.
6. Do not patch/retry if any R2 validation fails.

## Required exact Git blobs

Verify exactly:

```powershell
git rev-parse HEAD:src/idx_trade/v4_x1_clean_forward_score.py
git rev-parse HEAD:src/idx_trade/v4_x1_clean_eod_pipeline.py
git rev-parse HEAD:src/idx_trade/v4_x1_clean_eod_legacy_compat.py
git rev-parse HEAD:scripts/run_v4_x1_clean_forward_score.py
git rev-parse HEAD:scripts/run_v4_x1_clean_forward_readiness.py
git rev-parse HEAD:scripts/run_forward_eod_v4_x1_clean_pipeline.ps1
git rev-parse HEAD:scripts/update_forward_eod_task_v4_x1_clean.ps1
git rev-parse HEAD:tests/test_v4_x1_clean_forward_score.py
git rev-parse HEAD:tests/test_v4_x1_clean_eod_pipeline.py
git rev-parse HEAD:tests/test_v4_x1_clean_prospective_contract.py
git rev-parse HEAD:config/ranking_v4_x1_clean_prospective_score_v1.json
git rev-parse HEAD:docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_SCORE_PREPARED.md
git rev-parse HEAD:docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_STATIC_GUARD_REMEDIATED.md
```

Expected in that order:

- `f00528422a42835e5a969bfe503e29f91e0bf957`
- `2ce4fbcb9baec5c39ced4fadaaf58dc4d73a6216`
- `b78f020992e36fd1ba68027911e79bdb07e4da08`
- `c63e1a3e36f34dd4210e9dbb951dda9ae90a64ec`
- `07c38a0e27a0acfb7f5af49a7ea9b8b8fb822e1d`
- `5b3c3939ae87ce666bb9b1cd02ae4689d743122d`
- `7b06fa4914c090a5aa76f767347de71bd9dd95a1`
- `53f2d6648dcde43c765ac754b10c09eeb2f1643d`
- `778fb2d2b2027b84510a3d1db608e0c09c29ae51`
- `77582e2ff068897fbe8f0d3779216aebc9bf54b8`
- `fbdbed664259cf685a71dbbfebcc38ba7e558c92`
- `690e5eb2a3e903b2e1165523c2c363b8bfbfd5ec`
- `177b95214c49f0c44748389aaef5ef20d3881267`

Any mismatch => STOP.

## Focused validation

Run exactly:

```powershell
python -m pytest -q `
  tests/test_v4_x1_clean_forward_score.py `
  tests/test_v4_x1_clean_eod_pipeline.py `
  tests/test_v4_x1_clean_prospective_contract.py `
  tests/test_v4_x1_forward_score_contract.py `
  tests/test_v4_x1_eod_pipeline.py `
  tests/test_v4_x1_eod_legacy_compat.py `
  tests/test_v4_x1_eod_task_contract.py `
  tests/test_v4_x1_forward_readiness_contract.py `
  tests/test_forward_eod_runner.py `
  tests/test_forward_ohlcv.py

python -m py_compile `
  src/idx_trade/v4_x1_clean_forward_score.py `
  src/idx_trade/v4_x1_clean_eod_pipeline.py `
  src/idx_trade/v4_x1_clean_eod_legacy_compat.py `
  scripts/run_v4_x1_clean_forward_score.py `
  scripts/run_v4_x1_clean_forward_readiness.py

git diff --check
```

Any failure => STOP without patch/retry.

## Required external inputs

Accepted clean model root:

`D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1`

Required model manifest SHA-256:

`30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`

Accepted model SHA-256 values:

- CONTROL H5 `f727b10c6ea72c9ca7b447977ed4fa9cd3b5b32adb81793921c425d9085665b2`
- CONTROL H10 `737be8c47fe2d689dab09950a931c1339039ed8ae379b79f0bfd5a8c2e7605db`
- CHALLENGER H5 `d8a73d03ff72ab82826ef4e1be5e2073f6a61a5bb01b4e4268428436dc5eb082`
- CHALLENGER H10 `935a6f9aeaa2ca30a4016819e3848d284eb677e38153a7bd3126da0c33a9f95d`

Accepted clean panel SHA-256:

`25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`

Expected root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_20260820`

Accepted clean security master SHA-256:

`51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`

Expected root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_stage_b_final_20260820`

If filenames are ambiguous, resolve by SHA-256 and report the exact selected paths.

## Read-only scheduled-task inspection

Inspect existing Windows task `IDXTrade-ForwardEOD` **read-only**. Record:

- task state;
- action executable + arguments;
- working directory;
- daily trigger times;
- AtLogOn presence;
- canonical runtime root parsed from existing action;
- current model root parsed from existing action.

Do not call `Set-ScheduledTask`, `Register-ScheduledTask`, or `scripts/update_forward_eod_task_v4_x1_clean.ps1`.

The runtime root must come from the existing task/action or existing runtime configuration. Do not invent a second runtime/registry.

## Read-only readiness

Only after validation passes and exact paths are resolved, run:

```powershell
python scripts/run_v4_x1_clean_forward_readiness.py `
  --runtime-root "<EXISTING_CANONICAL_RUNTIME_ROOT_FROM_TASK>" `
  --x1-model-root "D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1" `
  --clean-panel "<EXACT_CLEAN_PANEL_PATH>" `
  --clean-security-master "<EXACT_CLEAN_SECURITY_MASTER_PATH>" `
  --observed-by "2026-08-20T12:08:44+00:00"
```

This is read-only. It must not score, fit, mutate the registry/counter/task, access outcomes, or call providers.

Expected initial clean counter: `0/100`. Nonzero => STOP for review.

Valid readiness states include:

- `V4_X1_CLEAN_FORWARD_READYNESS_WAITING_FIRST_POST_FREEZE_SESSION`
- `V4_X1_CLEAN_FORWARD_READYNESS_CANDIDATE_AVAILABLE_SCORE_NOT_RUN`
- `V4_X1_CLEAN_FORWARD_READYNESS_BLOCKED_CANONICAL_HISTORY_GAP`

A candidate does not authorize scoring.

## Freshness boundary

Freeze: `2026-08-20T12:08:44Z` / `2026-08-20T19:08:44+07:00`.

For a future counter-eligible session, both canonical session EOD and actual `DATA_READY` completion must be strictly after freeze. Same-Jakarta-date anti-backfill remains mandatory. Late catch-up can repair causal history but gets zero prospective counter credit.

Do not manually infer the first eligible session.

## Explicit prohibitions

- no scheduled-task mutation;
- no clean EOD pipeline execution;
- no direct real-session score CLI;
- no registry/counter edits;
- no old-X1 counter reuse;
- no outcome access;
- no provider addition;
- no feature/session/CA80/security-master policy/model changes;
- no V4-X2 semantics.

## Required report

Return:

- branch + HEAD and clean/synced state;
- canonical TEAM_STATUS claim/review commit;
- 13/13 exact blob verification;
- focused pytest result/count;
- py_compile and diff-check;
- chosen clean panel/master/model paths + SHA checks;
- existing task state/action/triggers + canonical runtime root;
- readiness status;
- clean counter completed/target/remaining/sessions;
- candidate session if any;
- history gaps if any;
- ignored backfills/reasons;
- clean historical panel last date;
- model manifest SHA + freeze boundary;
- all read-only safety flags;
- `scheduled_task_mutated=false`;
- `score_capture_performed=false`.

Update only this canonical readiness lane to `REVIEW`, then STOP.
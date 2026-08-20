# Handoff — V4-X1 Clean Prospective Local Validation + Read-Only Readiness

Branch: `integration/v4-x1-clean-prospective-score-v1`  
Scope: validation and read-only readiness only. **No deployment and no score capture.**

## Authorization

Controlling checkpoint:

- `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_SCORE_PREPARED.md`
- checkpoint blob `690e5eb2a3e903b2e1165523c2c363b8bfbfd5ec`
- decision `V4_X1_CLEAN_PROSPECTIVE_SCORE_PREPARED_READONLY_LOCAL_READINESS_AUTHORIZED`

Machine contract:

- `config/ranking_v4_x1_clean_prospective_score_v1.json`
- config blob `38a0357d9b039c651003354f4894add3f82d156a`
- `deployment_authorized=false`
- `score_capture_authorized=false`

Do not reinterpret this handoff as deployment authorization.

## Before local work

1. Fetch/read latest `origin/main:coordination/TEAM_STATUS.md`.
2. Confirm no duplicate `ACTIVE` owner for `V4-X1 clean prospective score/readiness`.
3. Add/update only that canonical main row to `ACTIVE` for this readiness pass, preserving every other row.
4. Checkout this branch and fast-forward to remote.
5. Preserve unrelated untracked work using a named stash including untracked files if required. Do not delete it.
6. Worktree must be clean before validation/readiness.
7. Inspect the existing Windows scheduled task `IDXTrade-ForwardEOD` read-only and record its current action, triggers, repo root, runtime root, model root, and task state. **Do not modify it.**

## Required local external inputs

Accepted clean model root:

`D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1`

Required model manifest SHA-256:

`30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`

Required models:

- CONTROL H5 `f727b10c6ea72c9ca7b447977ed4fa9cd3b5b32adb81793921c425d9085665b2`
- CONTROL H10 `737be8c47fe2d689dab09950a931c1339039ed8ae379b79f0bfd5a8c2e7605db`
- CHALLENGER H5 `d8a73d03ff72ab82826ef4e1be5e2073f6a61a5bb01b4e4268428436dc5eb082`
- CHALLENGER H10 `935a6f9aeaa2ca30a4016819e3848d284eb677e38153a7bd3126da0c33a9f95d`

Accepted clean panel SHA-256:

`25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`

Expected under the accepted Stage-A clean root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_20260820`

Accepted clean security master SHA-256:

`51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`

Expected under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_stage_b_final_20260820`

If exact filenames are ambiguous, resolve by SHA-256. Multiple byte-identical copies are acceptable; choose deterministically and report the path.

The canonical forward **runtime root must be obtained from the existing `IDXTrade-ForwardEOD` task/action or existing runtime configuration**. Do not invent a new runtime root and do not create a second registry.

## Exact preparation blobs

Before readiness, verify:

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
```

Expected respectively:

- `f00528422a42835e5a969bfe503e29f91e0bf957`
- `2ce4fbcb9baec5c39ced4fadaaf58dc4d73a6216`
- `b78f020992e36fd1ba68027911e79bdb07e4da08`
- `c63e1a3e36f34dd4210e9dbb951dda9ae90a64ec`
- `07c38a0e27a0acfb7f5af49a7ea9b8b8fb822e1d`
- `5b3c3939ae87ce666bb9b1cd02ae4689d743122d`
- `7b06fa4914c090a5aa76f767347de71bd9dd95a1`
- `c89bfab7173cd0355739cb3ec7960d5d3ea58f8a`
- `778fb2d2b2027b84510a3d1db608e0c09c29ae51`
- `77582e2ff068897fbe8f0d3779216aebc9bf54b8`
- `38a0357d9b039c651003354f4894add3f82d156a`
- `690e5eb2a3e903b2e1165523c2c363b8bfbfd5ec`

If any differs: STOP. Do not patch during this handoff.

## Focused local validation

Run:

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

Any failure => STOP. Do not patch/retry under this readiness authorization.

## Read-only scheduled-task inspection

Run/read only; do not call `Set-ScheduledTask`, `Register-ScheduledTask`, or the clean updater.

At minimum report:

- TaskName
- State
- current action executable + arguments
- WorkingDirectory
- daily trigger times
- whether AtLogOn exists
- runtime root parsed from the action
- current model root parsed from the action

This establishes the existing canonical runtime that must be reused.

## Read-only readiness command

After resolving exact paths, run only:

```powershell
python scripts/run_v4_x1_clean_forward_readiness.py `
  --runtime-root "<EXISTING_CANONICAL_RUNTIME_ROOT_FROM_TASK>" `
  --x1-model-root "D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1" `
  --clean-panel "<EXACT_CLEAN_PANEL_PATH>" `
  --clean-security-master "<EXACT_CLEAN_SECURITY_MASTER_PATH>" `
  --observed-by "2026-08-20T12:08:44+00:00"
```

This script must remain read-only:

- no provider/network calls;
- no model score;
- no model fit;
- no registry mutation;
- no scheduled-task mutation;
- no realized/protected outcome access.

Expected clean counter before deployment acceptance:

`0 / 100`

If counter is nonzero: STOP for independent review.

Possible valid readiness outcomes:

- `V4_X1_CLEAN_FORWARD_READYNESS_WAITING_FIRST_POST_FREEZE_SESSION`
- `V4_X1_CLEAN_FORWARD_READYNESS_CANDIDATE_AVAILABLE_SCORE_NOT_RUN`
- `V4_X1_CLEAN_FORWARD_READYNESS_BLOCKED_CANONICAL_HISTORY_GAP`

A candidate does **not** authorize scoring during this handoff.

## Freshness boundary

Clean freeze boundary:

`2026-08-20T12:08:44Z` / `2026-08-20T19:08:44+07:00`

Both must be strictly after it:

1. canonical EOD availability of the signal session;
2. actual canonical DATA_READY completion.

The existing same-Jakarta-date anti-backfill rule also remains required. Late catch-up can close causal history only and receives zero clean prospective counter credit.

Do not infer the first eligible calendar date manually.

## Explicitly prohibited in this handoff

- do not run `scripts/update_forward_eod_task_v4_x1_clean.ps1`;
- do not run the clean EOD pipeline;
- do not run `scripts/run_v4_x1_clean_forward_score.py` against a real session;
- do not score even if readiness reports a candidate;
- do not edit model-run rows;
- do not reset/reuse the old V4-X1 counter;
- do not access outcomes;
- do not add data providers;
- do not change the security-master policy;
- do not change feature/session/CA80/model semantics;
- do not mix V4-X2.

## Required report

Return:

- branch + HEAD, clean/synced state;
- canonical TEAM_STATUS coordination commit for readiness claim/review;
- exact blob verification PASS/FAIL;
- focused pytest count/result;
- py_compile PASS/FAIL;
- git diff --check PASS/FAIL;
- exact chosen clean panel/master/model paths + SHA verification;
- existing `IDXTrade-ForwardEOD` task state/action/triggers and resolved canonical runtime root;
- readiness status;
- clean counter completed/target/remaining and sessions;
- candidate first score session, if any;
- canonical history gaps, if any;
- ignored post-freeze backfills/reasons;
- historical clean panel last date;
- model manifest SHA;
- freeze boundary;
- all read-only safety flags;
- confirmation `scheduled_task_mutated=false`;
- confirmation `score_capture_performed=false`.

Update only this clean prospective readiness lane in canonical `TEAM_STATUS` to `REVIEW`, then STOP for independent review.
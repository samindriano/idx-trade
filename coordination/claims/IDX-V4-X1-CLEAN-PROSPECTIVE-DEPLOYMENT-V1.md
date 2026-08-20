# Claim — V4-X1 Clean Prospective Deployment V1

Date: 2026-08-20 (Asia/Jakarta)
Status: `WAITING_DEPLOYMENT_AFTER_20_35_WIB`
Owner: `ChatGPT/V4-X1-Clean-Prospective-Deployment`
Branch: `integration/v4-x1-clean-prospective-score-v1`

## Parent readiness

Readiness R2 accepted:

- HEAD `4bd588f7e7d862dd148328efc3aba544f8b47433`;
- 13/13 frozen blobs PASS;
- 54 focused tests PASS;
- py_compile PASS;
- diff-check PASS;
- readiness `V4_X1_CLEAN_FORWARD_READYNESS_WAITING_FIRST_POST_FREEZE_SESSION`;
- counter `0/100`;
- no candidate and no canonical history gap;
- canonical REVIEW commit `b90c2501c5c75837ead2472a982c063b6af4d34e`.

Controlling deployment checkpoint:

- `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_READINESS_ACCEPTED_DEPLOYMENT_AUTHORIZED.md`
- blob `a18621a03cdd9168e6b9cd0e625144e3eb3bb2c1`
- verdict `V4_X1_CLEAN_PROSPECTIVE_READINESS_ACCEPTED_DEPLOYMENT_ONLY_AUTHORIZED`

Controlling deployment contract:

- `config/ranking_v4_x1_clean_prospective_deployment_v1.json`
- blob `7919b21f3bf5451cc68687ee2fc2cf25b341fca2`

## Scope

Exactly one mutation attempt of existing Windows scheduled task `IDXTrade-ForwardEOD` to use the accepted clean V4-X1 EOD adapter.

No second task, runtime, provider path, registry, or counter is permitted.

## Timing guard

Do not mutate before `2026-08-20T20:35:00+07:00`.

Before mutation the existing task must:

- be `Ready`;
- still point to old model root `D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1`;
- use canonical runtime `D:\Documents\Project\idx-trade-data-gate-20260808v`.

This timing avoids racing the existing 20:30 Jakarta trigger.

## Mutation boundary

Authorized updater only:

`scripts/update_forward_eod_task_v4_x1_clean.ps1`

Git blob:

`7b06fa4914c090a5aa76f767347de71bd9dd95a1`

Expected clean pipeline blob:

`scripts/run_forward_eod_v4_x1_clean_pipeline.ps1` = `5b3c3939ae87ce666bb9b1cd02ae4689d743122d`

The task must retain daily 18:30/19:30/20:30 Jakarta triggers plus AtLogOn.

## Prohibited during deployment

- no manual task start;
- no manual clean EOD pipeline run;
- no direct score CLI;
- no registry/counter edits;
- no outcome access;
- no model fit/retune;
- no historical/backfill score;
- no feature/session/CA80/security-master policy changes;
- no V4-X2 semantics.

After successful mutation, automatic future scheduled scoring is authorized only under the frozen clean prospective contract.

Canonical `main:coordination/TEAM_STATUS.md` was read immediately before this deployment preparation. The clean readiness lane is `REVIEW`; no duplicate active clean deployment owner was present. The local deployment agent must make only the minimal canonical lane update required for deployment and preserve all unrelated rows.

# V4-X1 Clean Prospective — Readiness Accepted / Deployment Authorized

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `integration/v4-x1-clean-prospective-score-v1`

## Decision

`V4_X1_CLEAN_PROSPECTIVE_READINESS_ACCEPTED_DEPLOYMENT_ONLY_AUTHORIZED`

Readiness R2 is independently accepted.

Accepted local evidence:

- branch/head `integration/v4-x1-clean-prospective-score-v1 @ 4bd588f7e7d862dd148328efc3aba544f8b47433`;
- 13/13 frozen Git blobs PASS;
- focused pytest `54 passed`;
- `py_compile` PASS;
- `git diff --check` PASS;
- readiness status `V4_X1_CLEAN_FORWARD_READYNESS_WAITING_FIRST_POST_FREEZE_SESSION`;
- clean prospective counter `0/100`;
- candidate session none;
- canonical history gaps none;
- ignored backfills none;
- historical clean panel last date `2026-07-31`;
- provider/network/model-fit/model-score/outcome/registry mutation all false;
- scheduled-task mutation false;
- score capture false;
- canonical readiness REVIEW commit `b90c2501c5c75837ead2472a982c063b6af4d34e`.

Pinned accepted external identities remain:

- clean panel SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`;
- clean security master SHA-256 `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`;
- clean four-model manifest SHA-256 `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`;
- conservative prospective freeze boundary `2026-08-20T12:08:44Z` (`19:08:44 WIB`).

## Operational observation

The existing Windows task `IDXTrade-ForwardEOD` remains `Ready` and still points to the prior V4-X1 model root:

`D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1`

Canonical runtime root is:

`D:\Documents\Project\idx-trade-data-gate-20260808v`

Existing triggers remain daily `18:30`, `19:30`, `20:30` Asia/Jakarta plus AtLogOn.

## Deployment authorization

Deployment authorization is intentionally separated from the immutable readiness-preparation config.

New controlling deployment contract:

`config/ranking_v4_x1_clean_prospective_deployment_v1.json`

It authorizes exactly one migration of the existing `IDXTrade-ForwardEOD` task to the accepted clean V4-X1 pipeline.

Because independent acceptance occurred immediately before the scheduled 20:30 Jakarta trigger, task mutation must **not** race that trigger. The migration may start only after `2026-08-20T20:35:00+07:00` and only when the task is again `Ready`.

Deployment is task-mutation only. It does not authorize:

- manually invoking the clean EOD pipeline;
- manually invoking score capture;
- manually starting the scheduled task after migration;
- modifying the registry/counter;
- accessing outcomes;
- fitting or retuning models;
- changing feature/session/CA80/security-master semantics;
- mixing V4-X2.

## Automatic forward scoring after migration

After successful scheduler migration, future scheduled canonical EOD runs are authorized to create clean V4-X1 scores only under the already frozen prospective rules:

- clean model id `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`;
- counter starts at `0/100`;
- fresh-only;
- both canonical EOD and actual `DATA_READY` completion must be strictly after the freeze boundary;
- same-Jakarta-date anti-backfill remains mandatory;
- late catch-up is causal-history-only and receives zero clean counter credit;
- outcome vault stays locked until `100/100` and session-100 H10 maturity.

The first eligible observation is not manually inferred or backfilled. The runtime determines it from immutable canonical evidence.

## Failure policy

Any deployment precondition failure must stop before task mutation.

If the single task update attempt fails or post-update verification fails:

- stop;
- do not rerun automatically;
- do not run the pipeline manually;
- do not score manually;
- preserve the task state and report for review.

## Next

`AFTER_20_35_WIB_DEPLOY_EXISTING_TASK_ONCE_VERIFY_ONLY_THEN_WAIT_FOR_FIRST_FRESH_SCHEDULED_SESSION`

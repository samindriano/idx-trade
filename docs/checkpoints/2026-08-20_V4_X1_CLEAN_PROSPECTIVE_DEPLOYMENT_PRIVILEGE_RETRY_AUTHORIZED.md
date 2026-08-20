# V4-X1 Clean Prospective — Deployment Privilege Retry Authorized

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `integration/v4-x1-clean-prospective-score-v1`

## Decision

`V4_X1_CLEAN_PROSPECTIVE_DEPLOYMENT_PRIVILEGE_RETRY_AUTHORIZED`

The first Deployment V1 attempt is accepted as a fail-closed **non-mutating operational failure**. It exited at the updater's built-in Windows Administrator privilege check before `Set-ScheduledTask` was reached.

This is not a scientific, model, data, prospective-contract, or scoring failure.

## Accepted first-attempt evidence

- branch/head at attempt: `3e20bc32ecb5ec26860a3a0f4974bd55b223e689`;
- canonical TEAM_STATUS REVIEW commit: `0eb7684fe31d59fc79be482c7ab82637af6e501f`;
- pre-mutation time: `2026-08-20 20:37:50 Asia/Jakarta`;
- timing gate PASS;
- frozen blobs `6/6 PASS`;
- model manifest SHA-256 `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`;
- panel SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`;
- security-master SHA-256 `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`;
- task state before attempt `Ready`;
- LastRunTime `2026-08-20T20:30:01+07:00`;
- triggers `18:30`, `19:30`, `20:30` plus AtLogOn;
- canonical runtime root `D:\Documents\Project\idx-trade-data-gate-20260808v`;
- pre-task XML SHA-256 `15e07c4b7d8cfb64f1b10972b0c79cd6bd1b17a4cbe2b6947020c2342d6ef4eb`;
- updater invocation exactly once;
- failure: `Administrator PowerShell is required to update scheduled task: IDXTrade-ForwardEOD`;
- `Set-ScheduledTask` not reached;
- `scheduled_task_mutated=false`;
- no manual task start, pipeline run, score capture, registry/counter mutation, provider/model/outcome access.

Because the first handoff's retry prohibition applied to that handoff and the attempt made **zero mutation**, an independent new privilege-only deployment retry is scientifically and operationally safe.

## Retry boundary

New machine contract:

`config/ranking_v4_x1_clean_prospective_deployment_privilege_retry_v1.json`

The retry is authorized exactly once under a new handoff and only if the process is already elevated as Windows Administrator **before** invoking the updater.

Required preconditions:

1. latest canonical TEAM_STATUS read and this deployment lane minimally claimed;
2. branch clean/synced;
3. frozen deployment/updater/pipeline identities unchanged;
4. accepted model/panel/security-master hashes exact;
5. existing task state `Ready`;
6. existing task action still points to the old V4-X1 pipeline/model root `D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1`;
7. a read-only clean readiness check still reports clean counter `0/100`;
8. current process Administrator check PASS.

If the process is not elevated, stop before invoking the updater. Do not consume the authorized retry.

## Exactly one retry

Only after all preconditions PASS, invoke the frozen updater exactly once.

No code patch, pipeline patch, model change, scoring, manual task start, or outcome access is authorized.

After the updater, verify read-only:

- task remains `Ready`;
- action points to clean pipeline, clean model root, clean panel, clean security master, and frozen observed-by boundary;
- triggers remain `18:30`, `19:30`, `20:30` plus AtLogOn;
- LastRunTime does not change during scheduler mutation;
- read-only clean readiness remains `0/100` immediately after deployment;
- no score was captured during deployment.

If updater or post-verification fails, stop. No second retry under this handoff.

## Scientific state unchanged

- clean forward counter remains expected `0/100`;
- 2026-08-20 remains ineligible for clean prospective credit;
- first eligible observation remains runtime-determined from future immutable canonical evidence;
- outcome vault remains locked until `100/100` plus session-100 H10 maturity;
- V4-X2 remains separate.

## Next

`ADMINISTRATOR_PRIVILEGED_SCHEDULER_MIGRATION_RETRY_ONCE_THEN_VERIFY_ONLY`

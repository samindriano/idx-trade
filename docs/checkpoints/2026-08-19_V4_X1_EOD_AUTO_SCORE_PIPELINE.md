# V4-X1 EOD Auto-Score Pipeline V1

Date: 2026-08-19 (Asia/Jakarta)

Branch: `integration/v4-x1-eod-auto-score-v1`

Status: `IMPLEMENTED_PENDING_LOCAL_VALIDATION_AND_DEPLOYMENT`

## Starting state

The accepted standalone V4-X1 scorer already committed the first clean prospective observation:

- first clean session: `2026-08-19`;
- V4-X1 prospective counter: `1/100`;
- score artifact SHA-256: `aafcea7e594dd9a0cdd8c4483a5fdfd11e75992cdb259dc8a033c51d05f32056`;
- score manifest SHA-256: `9fc47fa650b05c4fca5344cdf0ed309fd44ece5d21eb84965e8c36a59e830b9d`;
- frozen model fingerprint: `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`.

No outcome was opened and no model was refit or retuned.

This lane operationalizes future score capture only. It does not change the accepted standalone artifact or frozen science.

## Pipeline contract

One scheduled invocation is now:

`canonical EOD catch-up -> EOD success gate -> same-day prospective gate -> frozen V4-X1 scorer`

The canonical EOD engine remains the only market-data capture owner. The V4-X1 layer is a downstream consumer and does not call a provider.

If EOD fails, X1 is not run. If X1 fails, the already committed canonical EOD snapshot is left intact and the process exits non-zero so the Windows scheduler can retry.

## Morning catch-up remediation

The prior EOD runner returned `BEFORE_EOD_CUTOFF` before inspecting older missing sessions. That meant an AtLogOn run in the morning could not repair yesterday until the evening trigger.

V1 changes the operational boundary:

- before 18:00 Asia/Jakarta, today's session remains forbidden;
- prior closed sessions may be caught up immediately;
- between 17:00 and 18:00 the runner still clamps `closed_through` to the previous calendar date even though the lower-level helper would otherwise allow today after 17:00;
- at/after 18:00, the normal canonical closed-through rule applies.

The runner filters the loaded calendar to `session <= closed_through` before selecting a missing session, so an already-present future/today calendar row cannot bypass the boundary.

## Prospective anti-backfill guard

A separate deployment guard prevents late data repair from becoming retrospective X1 evidence.

A new score may be committed only when:

1. the scorer's existing model-freeze freshness gates pass;
2. the candidate session equals the current Jakarta calendar date at pipeline invocation; and
3. canonical `DATA_READY.completed_at`, converted to Asia/Jakarta, is on that same session date.

Any older pending post-freeze session is classified:

`CONTINUITY_ONLY_NOT_X1_COUNTER`

with an explicit reason such as:

- `X1_SCORE_WINDOW_EXPIRED_NOT_SAME_JAKARTA_DATE`, or
- `X1_DATA_READY_COMPLETED_AFTER_SESSION_DATE`.

This operational rule is deliberately stricter than the original freeze-only gate. It is not a model/science change and cannot improve historical performance. Its purpose is to guarantee that a laptop waking days later can repair causal history without manufacturing a retrospective prospective observation.

The already accepted 2026-08-19 X1 #1 is unaffected: its DATA_READY and score were both committed on 2026-08-19 after the frozen model timestamp and before the next session.

## Implementation

New:

- `src/idx_trade/v4_x1_eod_pipeline.py`
- `scripts/run_forward_eod_v4_x1_pipeline.ps1`
- `tests/test_v4_x1_eod_pipeline.py`

Modified:

- `src/idx_trade/forward_eod_runner.py`
- `tests/test_forward_eod_runner.py`

The deployment orchestrator temporarily narrows the accepted standalone scorer's internal pending-session selector to the operational same-day subset for that single process only. The underlying standalone scorer source/model/science remains unchanged.

## Pipeline statuses

Success statuses are:

- `PIPELINE_OK_PRIOR_SESSION_CATCHUP_ONLY_BEFORE_EOD`
- `PIPELINE_OK_X1_NEW_SCORE_COMMITTED`
- `PIPELINE_OK_X1_EXISTING_SCORE_VERIFIED`
- `PIPELINE_OK_NO_ELIGIBLE_SAME_DAY_X1_SCORE`

Failure boundaries include:

- `EOD_FAILED_X1_NOT_RUN`
- `PIPELINE_FAILED`

Every run writes its own JSON log plus `latest.json` below:

`forward_monitoring/eod_automation/v4_x1_pipeline/`

The existing EOD automation log remains separate and unchanged.

## Hard guards

The deployment lane does not authorize:

- protected/fresh-forward outcome access;
- H5/H10 realization materialization;
- IC, return, hit-rate, PnL, Sharpe, or other performance evaluation;
- model fitting or retuning;
- feature/science changes;
- V4-X2;
- a second market-data capture/provider path;
- Path Risk/Probability/Expected Payoff work;
- portfolio optimization.

## Required local validation

Before deployment, run on the exact branch checkout:

```powershell
python -m pytest -q `
  tests/test_forward_eod_runner.py `
  tests/test_v4_x1_forward_readiness_contract.py `
  tests/test_v4_x1_forward_score_contract.py `
  tests/test_v4_x1_eod_pipeline.py

git diff --check
git status --short
```

Then run the pipeline manually against the actual runtime. Since 2026-08-19 X1 #1 already exists, a same-evening smoke should verify the existing immutable score rather than rewrite it:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\run_forward_eod_v4_x1_pipeline.ps1 `
  -RepoRoot $PWD.Path `
  -RuntimeRoot "D:\Documents\Project\idx-trade-data-gate-20260808v" `
  -X1ModelRoot "D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1" `
  -PythonExe "C:\Users\Sam\AppData\Local\Programs\Python\Python313\python.exe"
```

Expected for the 2026-08-19 same-day rerun:

`PIPELINE_OK_X1_EXISTING_SCORE_VERIFIED`

with the existing score artifact/manifest hashes unchanged.

Only after this smoke is accepted should the Windows `IDXTrade-ForwardEOD` launcher be repointed from `run_forward_eod_catchup.ps1` to `run_forward_eod_v4_x1_pipeline.ps1` and tested through `Start-ScheduledTask` plus a real timer trigger.

## Deployment boundary

Do not modify the current working Windows scheduled task until the exact branch tests and manual pipeline smoke pass. Keep the currently healthy EOD task operational until the replacement wrapper is proven locally.

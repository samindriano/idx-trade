# Handoff

from: MAIN / parent ChatGPT
to: LOCAL / Codex verification only
task_id: IDX-WEB-FORWARD-MONITOR-START-ANCHOR-VERIFY
branch: `frontend/model-monitoring-v1`
scope: Verify the 2026-08-10 operator monitoring anchor fix. Do not implement or edit repository code.

## Expected contract

- `FRESH_FORWARD_CUTOFF` remains 2026-07-31.
- operator-facing `FORWARD_MONITOR_START_DATE` is 2026-08-10.
- pre-2026-08-10 registry/artifact rows may physically remain but are ignored by active monitoring status/counts/history.
- `/api/monitor/status` must report `monitor_start_date=2026-08-10`.
- with no eligible Aug-10+ DATA_READY session, `next_missing_session` must be 2026-08-10 once calendar is synced/available.
- UI target-date minimum must be 2026-08-10 and stale 2026-08-03 client state must clamp forward.

## Allowed actions

1. fast-forward pull latest `origin/frontend/model-monitoring-v1` only;
2. verify tracked worktree is clean;
3. run `python -m pytest tests/test_forward_monitoring_runtime.py tests/test_forward_monitoring.py`;
4. run full pytest;
5. run `npm run build` in `apps/web`;
6. restart dev server so the new Python module and Next.js adapter are loaded;
7. GET `/api/monitor/status` and report `monitor_start_date`, `calendar_first_session`, `calendar_last_session`, `next_missing_session`, `data_ready_sessions`, and returned session dates;
8. open `/monitoring` and verify the target/date history no longer shows sessions before 10 Aug 2026.

## Prohibited

- no repository source edits;
- no push;
- no real POST capture;
- no model scoring;
- no H10 outcome/label access;
- no model refit/retraining;
- no deletion of pre-anchor local artifacts/registry rows;
- no force/reset/clean/rebase.

## Return

- local/remote HEAD;
- git status;
- targeted/full pytest results;
- Next build result;
- `/api/monitor/status` summary;
- confirmation UI starts at 10 Aug 2026;
- exact error if any.

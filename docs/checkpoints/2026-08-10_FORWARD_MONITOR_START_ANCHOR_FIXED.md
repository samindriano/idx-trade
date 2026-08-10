# Forward Monitor Start Anchor Fixed

Date: 2026-08-10 (Asia/Jakarta)
Branch: `frontend/model-monitoring-v1`

## Decision

The operator-facing V2 forward monitor starts on **2026-08-10**.

This is intentionally distinct from `FRESH_FORWARD_CUTOFF=2026-07-31`, which remains the research/development cutoff and must not be changed to solve a UI/runtime monitoring-anchor issue.

## Bug

The first monitoring implementation reused `FRESH_FORWARD_CUTOFF + 1 day` as its calendar start. That caused the dashboard to expose early-August sessions (for example 2026-08-03) as missing forward-monitor sessions even though the live operator monitoring contract was activated on 2026-08-10.

## Fix

Added `src/idx_trade/forward_monitoring_runtime.py` with an explicit:

`FORWARD_MONITOR_START_DATE = 2026-08-10`

The operator runtime now:

- syncs the monitoring calendar starting at 2026-08-10;
- filters any pre-2026-08-10 calendar rows from status/history;
- calculates `next_missing_session` only on or after 2026-08-10;
- counts DATA_READY snapshots only on or after 2026-08-10;
- filters model-run status to sessions on or after 2026-08-10;
- rejects explicit capture requests before 2026-08-10;
- preserves pre-anchor registry/artifact rows if they already exist, but ignores them for the active monitoring contract.

`apps/web/lib/monitor-runtime.ts` now invokes `idx_trade.forward_monitoring_runtime` rather than the unanchored base engine.

## Research boundary unchanged

This patch does **not** change:

- `FRESH_FORWARD_CUTOFF=2026-07-31`;
- frozen V2 model weights or SHA;
- H10 outcome-access rules;
- `FORWARD_OUTCOME_ACCESS_STARTED` status;
- any historical model metrics;
- any research-data/model artifact semantics.

Fresh-forward outcomes remain LOCKED.

## Regression coverage

Added `tests/test_forward_monitoring_runtime.py` covering:

1. pre-start calendar filtering;
2. exact Aug-10 calendar sync start;
3. rejection of pre-start capture requests;
4. exclusion of pre-start registry rows from counts/history/next-session logic.

## Local verification required

Only local execution remains:

- pull latest `frontend/model-monitoring-v1`;
- run targeted monitoring tests and full pytest;
- run `npm run build`;
- restart dev server;
- confirm `/api/monitor/status` reports `monitor_start_date=2026-08-10` and `next_missing_session=2026-08-10` when no eligible session has been recorded;
- do not run a real capture as part of this verification unless separately authorized.

# Handoff

from: Codex Luna xhigh
to: ChatGPT reviewer / MAIN
task_id: IDX-FOREIGN-FLOW-HISTORICAL-ACQUISITION-V1
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 32bb1390303b9103ac53c6faa4d521c1352ee940
branch: data/idx-foreign-flow-historical-acquisition-v1
head_commit: e232ee6fc4165817740950554708dc36dcd9f7c0

## Scope

Historical official IDX Stock Summary ForeignBuy/ForeignSell acquisition and
coverage census only. Unit is SHARES. Label provenance is
`OFFICIAL_IDX_HISTORICAL_EOD`; acquisition mode is
`RETROSPECTIVELY_ACQUIRED`. Session `t` data is usable only from official
session `t+1`; retrieval observation is not claimed to be publication time.

## Files changed

- `src/idx_trade/providers/idx_stock_summary.py`
  - added `prepare_session=True` option to the existing capture function;
  - historical runner prepares the same HTTP session once and continues to use
    the official `GetStockSummary` endpoint per date.
- `src/idx_trade/foreign_flow_historical.py`
  - official-session input validation;
  - raw-byte and normalized-artifact exclusive writes;
  - exact SHA/provenance manifests;
  - resumable/idempotent acquisition;
  - coverage census and CLI.
- `tests/test_foreign_flow_historical.py`
  - exclusive/resumable behavior;
  - fail-closed session errors;
  - tampered normalized artifact detection.
- `docs/checkpoints/2026-08-14_FOREIGN_FLOW_HISTORICAL_ACQUISITION_RESULT.md`

## External artifacts

Root:
`D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1`

Archive manifest SHA-256:
`fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`

Calendar SHA-256:
`2b597142190e7e7a3182b80c75dc3fec3e0bbbfe32948fb2d586b33b5844a536`

The external archive contains 1,288 complete session manifests and
1,129,024 normalized rows for 2021-04-01..2026-08-13. It has 0 acquisition
errors and 0 malformed/rejected rows materialized. 2018–2019 sampled dates
were empty; 2020-01-02 was complete but a complete 2020 official session
calendar was not established, so the bounded archive starts in 2021.

## Validation

Focused tests passed after implementation. Full pytest is required before this
handoff is considered complete; record the exact result in the final commit
and TEAM_STATUS update.

## Decision needed

Review whether `CONDITIONAL_PASS_BOUNDED_OFFICIAL_IDX_HISTORICAL_EOD` is
acceptable for the bounded 2021-04-01..2026-08-13 archive, and whether a
separate official-session acquisition task should be authorized before any
attempt to extend the archive into 2020.

## Prohibitions respected

No non-official provider, Financial PIT, Corporate Actions, PIT sector,
scheduler/ForwardEOD, O2, model, feature-performance, protected outcomes, or
forward counter work was performed.

# Stockbit Forward Reliability Remediation V1

Date: 2026-08-25 Asia/Jakarta
Branch: `fix/idx-forward-reliability-v1`
Source main: `2be7160f20184e489f7a9f82a0d6aac890622c7e`
Implementation commit: `85b6f317`

Final branch head: `2658a56dfe7a5c27f98ec2adaa95d89366f448ae`

## Scope

This lane fixes two narrow reliability defects in the existing Stockbit Stream
capture engine. It does not change the all-ticker `DATA_READY` contract,
provider schema, model, Decision, sizing, execution, counters, or outcomes.

## Findings and fixes

1. A resumed run charged the provider-call budget for already verified `OK`
   records. The budget now counts only the pending universe rows, while the
   monthly reserve and bounded retry policy remain unchanged.
2. If attempt 1 returned a retryable HTTP response and attempt 2 raised a
   `requests.RequestException`, attempt-1 response state could remain in local
   variables. The final record now contains exactly one terminal logical
   failure, with no stale response acceptance or normalized output.
3. Every retryable physical response is retained as immutable diagnostic raw
   evidence. A terminal request exception is retained as one final request
   record; all physical attempts remain auditable.

## 2026-08-24 read-only operational evidence

External runtime root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\stockbit_intraday_recurring_v1\sessions\2026-08-24`

- daily mode: `SHADOW`
- planned universe: 962 tickers
- activity-eligible fetches: 833
- no-activity skips: 129
- normalized points: 120,251
- synthetic fill: false
- HTTP 429 events: 0
- retries: 0
- request attempts: 962
- status rows: 962; successful rows: 833; no-activity HTTP-404 rows: 129
- final `shadow_certification_eligible`: true
- artifact manifest SHA: `0d4a878e92681dde6c82b0ddf7927502338082188ab301eeebba76e24ab8ac8e`

The 129 HTTP-404 observations match the same run's gate classification as
no-activity skips. They are not treated as successful market data and do not
create synthetic rows. The evidence is preserved outside Git and was not
overwritten by this task.

## Validation

- focused Stockbit capture/archive tests: 27 passed
- full pytest on the current source lineage: 78 passed, 0 failed
- `python -m py_compile src/idx_trade/stockbit_stream_capture_v2.py`: pass
- `git diff --check`: pass
- no provider call was made by this remediation
- no protected outcome access, marker write, model/Decision/sizing/execution,
  or forward-counter mutation occurred

## Boundary

The existing scheduler and 200/200 all-ticker readiness policy were not
changed. A future genuine scheduled run is required for live operational proof
of this branch; this checkpoint is an engineering/remediation result only.

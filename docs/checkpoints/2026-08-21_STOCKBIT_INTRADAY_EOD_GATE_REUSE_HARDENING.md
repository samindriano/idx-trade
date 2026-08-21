# Stockbit Intraday EOD-Gate Reuse Hardening V1

## Scope

The existing Stockbit intraday recorder remains the only intraday capture
path. This remediation only changes its post-close activity gate: when the
canonical `forward_monitoring` session already has a verified `DATA_READY`
official IDX Stock Summary for the exact date, the intraday runner reuses that
immutable evidence instead of making a second Zapi summary request.

The fallback Zapi request remains available when the canonical EOD artifact is
missing or fails any date, completeness, schema, or SHA check. All failures
remain fail-closed.

## Why

The existing post-close gate received HTTP 200 responses with
`recordsTotal=0` after the provider's publication timing window, so the
runner stopped before making any Stockbit chart requests. The EOD transaction
already acquired the same official snapshot successfully for the session, so
reusing it removes the duplicate request and the EOD/intraday race without
creating another recorder, API, database, or scheduler.

The earlier zero-row Zapi response is retained as immutable evidence. It is
not overwritten or treated as a successful market snapshot.

## Reuse contract

The EOD artifact is accepted only when:

- session and source dates exactly equal the requested Jakarta session;
- manifest status is `DATA_READY` and source is `IDX_OFFICIAL`;
- completeness is `COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE`;
- rows equal `records_total` and `records_filtered`;
- normalized ticker identity is unique;
- activity fields are finite and non-negative;
- raw and normalized SHA-256 values match the EOD manifest.

Gate metadata records the source paths, hashes, official source reference,
record counts, and observed retrieval time. The observed retrieval time is
not treated as historical publication time.

## Validation

- focused intraday tests: **26 passed**;
- `py_compile`: **PASS**;
- `git diff --check`: **PASS**;
- no model, outcome, counter, or provider artifact was changed by the code
  change.

## Remaining bounded recovery

The 2026-08-20 Stockbit `timeframe=today` session is not reconstructed after
provider rollover. The next eligible same-day run can use the EOD gate reuse
path for future sessions.

## Controlled recovery validation — 2026-08-21

The existing headless EOD catch-up runner was executed once after restoring the
official calendar. It completed `NO_MISSING_SESSION` and produced immutable
`DATA_READY` sessions for both 2026-08-20 and 2026-08-21. The earlier 2026-08-20
Stockbit intraday-only session remains unrecoverable after the provider's
`timeframe=today` rollover; it was not synthesized or overwritten.

EOD session results:

| session | model rows | session OHLCV SHA-256 | model-input SHA-256 |
|---|---:|---|---|
| 2026-08-20 | 834 | `cab1731da45c7b11d821e9b7720a87abfdcc9205dc497573b6f223c9779cb8f6` | `0d5820c9c14dfaa603b6b6a9cfc88b38e30713507ac53ff734f5658ecdf8fb98` |
| 2026-08-21 | 832 | `e65f33d536719cd7e3d5bf6988c45dd29cafc23634129252725136a0749d748a` | `6bd150d3944d4e00e8f04609a94c434a30d70dcafdf92d9b3a2fafc5724b9964` |

The clean V4-X1 prospective scorer was then run once for 2026-08-21 using the
existing scheduler's frozen 2026-08-20 19:08:44 WIB eligibility boundary. It
finished `DONE` with 294 score rows, artifact SHA-256
`fdb851aa13dfab7ac3501404352c6701c50dd6e79c79450c6995686b00a889a1`, manifest
SHA-256 `92a7e23542b11ae98d49bb0cb84feb35b897734887ee31237945b0a575fe0946`,
and the official model-run row is now `DONE` (the clean V4-X1 prospective
counter is therefore 1/100). The V4 manifest guards all remain false for
provider calls, model refit/retune, protected outcome access, and realized
forward outcome loading.

The repaired Stockbit intraday runner completed one current-session capture for
2026-08-21:

- `complete=true`, 962 attempted tickers, 832 successful tickers, 0 unfinished;
- 103,231 normalized points, 962 requests, 0 retries, 0 HTTP 429 events;
- 832 Stockbit fetches and 130 official no-activity skips;
- no duplicate IDX summary request (`idx_summary_call_made_this_run=false`);
- official gate source `IDX_OFFICIAL_EOD_REUSE`, source URL
  `https://www.idx.id/primary/TradingSummary/GetStockSummary?date=20260821`;
- intraday artifact manifest SHA-256
  `42507a7fd701f0e05bbd3028829c93a962f77de4a8829b5d72d585bebeafb0e2`;
- gate metadata SHA-256
  `41e81f355fcd1c7c4b14d79357ced379b4b8af09cdd0fadb3535c14fc86574d9`.

The Windows task remains enabled and `Ready`, uses the repaired headless
runner, and keeps its existing 18:30/19:30/20:30 WIB triggers with
`StartWhenAvailable`, `WakeToRun`, and `IgnoreNew`. No new scheduler or data
hierarchy was created. No Corporate Action scheduler/capture path exists in
the current runtime; CA remains a separate static/manual evidence lane and is
not claimed as automatically captured by this repair.

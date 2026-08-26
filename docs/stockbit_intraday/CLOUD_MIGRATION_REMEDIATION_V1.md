# Stockbit Intraday Cloud Migration Remediation V1

Date: 2026-08-26 Asia/Jakarta
Branch: `ops/stockbit-intraday-cloud-migration-v1`
Base main: `a76bf51a84059335bb70906d42243354440bd857`
Legacy implementation reference: `fix/stockbit-intraday-postclose-fix-v1@03d42988b16ced8d5c2656291c629ea3596f91f4`

## Goal

Port only the bounded, still-valid Stockbit intraday acquisition semantics into a current-main cloud lane, while fixing recovery/idempotency defects before any GitHub Actions/R2 activation.

This lane must not alter model science, Decision V2, Sizing V1, Execution V1, protected outcomes, prospective counters, Official Open authority, or the canonical EOD/CA contracts.

## Accepted legacy semantics to preserve

- provider contract: `provider=stockbit`, `interval=intraday`, `timeframe=today`;
- exact requested ticker identity;
- exact current Asia/Jakarta session date;
- no historical reconstruction after provider rollover;
- no synthetic minute data, interpolation, OHLCV invention, or forward fill;
- frozen same-day IDX active-stock universe with hashes;
- strict reuse of canonical same-session official EOD Stock Summary when available;
- conservative fetch when gate evidence is missing;
- monthly quota reserve and bounded retry behavior;
- raw provider evidence, normalized path rows, status evidence, and hashes.

## Remediations required before cloud activation

### R1 — explicit status classes

Do not use a single `retry_errors` boolean to decide all resume behavior.

Admissible terminal statuses:

- `SUCCESS`
- `SKIPPED_IDX_NO_ACTIVITY`

Retryable statuses:

- transient `REQUEST_ERROR`

Blocking terminal statuses:

- `EMPTY_SESSION`
- `NO_VALID_POINTS`
- `NON_CURRENT_SESSION`
- `IDENTITY_OR_PAYLOAD_ERROR`
- `MULTI_SESSION_PAYLOAD`
- `TRADING_DATE_METADATA_MISMATCH`
- `DUPLICATE_TIMESTAMP_CONFLICT`

Unknown statuses fail closed and are blocking.

A recovery run must retry retryable statuses, must not refetch admissible terminal statuses, and must never silently reinterpret a blocking status as success.

### R2 — completion semantics

`attempted == universe` is not sufficient for an admissible complete session.

The runtime must expose at least:

- observed ticker count;
- admissible terminal count;
- retryable count;
- blocking count;
- missing count;
- `all_observed`;
- `all_terminal`;
- `admissible_complete`.

Only `admissible_complete=true` may suppress later recovery triggers.

### R3 — retry/gate interaction

`SKIPPED_IDX_NO_ACTIVITY` is permanently terminal for the admitted same-session gate evidence. A retry mechanism must never turn it back into a pending Stockbit request.

### R4 — policy transition idempotency

A SHADOW/ENFORCE policy transition must be keyed by at least:

`(session_date, admitted_session_manifest_sha256)`.

Reapplying the identical event is a no-op. Reusing the same session date with a different manifest/event is a conflict and must fail closed. A crash between policy-state persistence and final summary persistence must not double-count one trading session.

### R5 — evidence immutability in cloud

Local `temporary.replace()` overwrite semantics must not be carried into R2 prospective evidence.

Cloud writes must use conditional create/write-once semantics:

- first write succeeds;
- byte-identical retry is idempotent;
- conflicting bytes at the same evidence key fail closed.

Mutable operational state, if any, must be separate from immutable market evidence.

### R6 — payload completeness wording

A post-close wall-clock gate does not prove that every traded ticker has a final trade near exchange close. The cloud artifact must not claim stronger completeness than the provider contract establishes.

Use wording equivalent to `POSTCLOSE_TODAY_PATH_OBSERVED` for accepted provider paths unless a stronger provider-level completeness contract is independently proven. Illiquid names must not be rejected merely because their last trade occurred earlier in the session.

### R7 — canonical calendar admission

GitHub Actions orchestration must consult the canonical IDX trading-session calendar before provider calls. Non-session dates must produce a zero-provider-call NOOP. Provider failures remain a second fail-closed layer, not the primary holiday detector.

## Migration order

1. Add pure recovery/status and policy-idempotency semantics with focused tests.
2. Port the bounded legacy capture/farm/daily implementation onto current main and make it consume those semantics.
3. Add immutable object-store adapter and R2 key contract.
4. Add canonical-calendar GitHub Actions orchestration.
5. Run offline/fake-provider tests.
6. Run isolated R2 conditional-write smoke without provider calls.
7. Run one controlled current-session cloud capture while Windows remains fallback.
8. Compare cloud vs Windows evidence for the same session.
9. Retire Windows only after one clean accepted future-session proof and explicit user authorization.

## Current verdict

`STOCKBIT_INTRADAY_CLOUD_MIGRATION_REMEDIATION_ACTIVE`

No cloud scheduler or provider call is authorized merely by this document.
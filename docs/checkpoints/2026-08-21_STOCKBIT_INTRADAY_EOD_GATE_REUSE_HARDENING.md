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

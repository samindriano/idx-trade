# E2E Baseline Paper V1 ? Generic Dividend Discovery Live Acceptance

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`

## Scope

Generalized prospective cash-dividend announcement discovery using the admitted direct IDX endpoint:

`/ListedCompany/GetAnnouncement`

This replaces the BBCA/date/SHA-hardcoded discovery logic used during the earlier source audit.

This checkpoint covers announcement discovery only.

It does not download attachments, certify dividend economics, mutate paper state, or authorize unattended execution.

## Implementation

Pure acquisition/parser module:

`src/idx_trade/forward_dividend_acquisition_v1.py`

Live capture:

`scripts/capture_forward_dividend_announcements_v1.py`

Tests:

`tests/test_forward_dividend_acquisition_v1.py`

Pinned provider:

- repository: `nichsedge/idx-bei`
- commit: `75d6c0f74fa360d225794c70c383348977de6798`

## Conservative classifications

The generic parser distinguishes:

- `CASH_DIVIDEND_CANDIDATE`
- `AMBIGUOUS_DIVIDEND_CANDIDATE`
- `UNSUPPORTED_NON_CASH_DIVIDEND`

Unrelated announcements are ignored.

Ticker mismatch, malformed schema, conflicting duplicate identities, and incomplete pagination fail closed.

## Offline real-evidence validation

The generic parser was run against the previously captured official BBCA announcement bytes without BBCA-specific logic inside the parser.

Observed:

- candidate count: `1`
- ticker: `BBCA`
- classification: `CASH_DIVIDEND_CANDIDATE`
- announcement ID: `20260819183103-005/CSG-IVR/2026_id-id`
- announcement number: `005/CSG-IVR/2026`
- title: `Jadwal Dividen Tunai Interim`
- attachment metadata rows: `3`

Verdict:

`GENERIC_DISCOVERY_REAL_BBCA_PASS`

## Live IDX smoke

Window:

`2026-08-18` through `2026-08-21`

Required tickers:

- `BBCA`
- `BBRI`
- `TLKM`

All requests returned HTTP 200 JSON and durable local bytes reproduced their manifest SHA-256.

Observed raw artifacts:

- BBCA:
  `6e8ced1891addecdb9a1029d064c75d072ebcbeb4319ad633d30e43fac004473`
- BBRI:
  `00e725800663ee2e92bbe0b610ce7c256d7de45cb2cea0f6f62c29a7b205be26`
- TLKM:
  `a2c4a75f1b60fc958916ad67d91f2704ee1f88642bf5252e37db81e30e766bb1`

Candidate count:

`1`

The candidate was the admitted BBCA interim cash-dividend announcement with three attachment metadata rows.

Verdict:

`GENERIC_DIVIDEND_DISCOVERY_LIVE_SMOKE_PASS`

## Regression

Generic acquisition tests:

`7 passed`

Existing CA/dividend regression:

`45 passed`

Combined focused suite:

`52 passed`

`git diff --check` PASS.

## Verdict

`E2E_GENERIC_DIVIDEND_DISCOVERY_LIVE_ACCEPTED`

## Remaining boundary

The discovery candidate is not yet a certified dividend event.

Next:

generic immutable attachment acquisition
? generic offline semantic review
? existing hash-bound `CertifiedCashDividend`
? durable registry.

Ambiguous or non-cash events remain fail closed.

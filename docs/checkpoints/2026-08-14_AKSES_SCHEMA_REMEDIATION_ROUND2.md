# Personal AKSes Portfolio Schema — Remediation Round 2

Date: 2026-08-14 Asia/Jakarta

Lane: `AKSes adapter schema V1`

Branch: `integration/schema-hardening-v2`

## Trigger

Independent review round 2 returned `REWORK` with three P1 findings:

1. direct JSON Schema validation did not reliably reject timezone-naive timestamps;
2. canonical JSON validation lacked a shared semantic gate for row arithmetic, failed-endpoint rows, duplicate identities and canonical detail counts;
3. `PORTFOLIO_SUMMARY` was omitted from canonical row reconciliation.

The reviewer also noted that `ksa_<64hex>` proved only shape, not factory origin.

## Remediation

### Timezone

The checked/runtime Draft 2020-12 schema now requires an explicit `Z` or numeric UTC offset in addition to `format: date-time`. The shared semantic layer independently parses the value, rejects naive timestamps and enforces `fetched_at >= snapshot_at`.

### Shared canonical semantic gate

New module `personal_portfolio/semantics.py` is the authoritative cross-field validator used by both direct canonical payload validation and the `PortfolioSnapshot` object path.

It enforces:

- canonical required endpoint order;
- successful endpoint arithmetic `observed_rows = accepted_rows + rejected_rows`;
- failed endpoint `observed_rows = accepted_rows = rejected_rows = 0` plus failure code;
- duplicate position identity rejection;
- duplicate cash identity rejection;
- CASH/EQUITY/MUTUAL_FUND/BOND/OTHER accepted-row reconciliation against canonical rows;
- COMPLETE/PARTIAL evidence semantics;
- timezone-awareness and timestamp ordering.

`validate_snapshot_payload()` now runs structural schema, minimization, then this semantic validator.

### Summary semantics

V1 freezes `PORTFOLIO_SUMMARY.accepted_rows` to one summary aggregate per represented non-empty canonical asset class. For example, one or more equities plus one or more cash balances imply two represented summary categories, regardless of the number of security rows.

This interpretation is intentionally provisional and fail-closed because audited unofficial clients expose summary category aggregates, while no real personal response has been accessed. A bounded sanitized response that proves different zero-category behavior requires an explicit contract review.

### Opaque subaccount hardening

`derive_subaccount_ref()` returns a dedicated `SubaccountRef` subtype created through a private factory token. New `PortfolioPosition` and `CashBalance` objects reject plain strings even when they match the opaque wire shape. Canonical deserialization rehydrates the subtype only after `validate_snapshot_payload()` succeeds.

This does not claim that persisted JSON itself can prove HMAC provenance; the wire schema can only enforce shape. Factory provenance is enforced at the Python ingestion boundary.

## Tests added

`tests/test_snapshot_semantic_gate.py` covers direct canonical-payload failures for naive timestamps, endpoint arithmetic, failed endpoint rows, duplicate positions/cash, detail count mismatch, summary mismatch and timestamp ordering.

`tests/test_subaccount_ref_factory.py` covers rejection of a manually supplied shape-valid `ksa_<64hex>` string and acceptance of a reference returned by the server-side factory.

Existing round-trip and round-1 hardening tests remain part of the review gate.

## Validation status

The remediation agent performed GitHub remote diff/import-graph consistency review and targeted logic checks. This runtime cannot obtain an exact Git checkout because outbound Git network access is unavailable, so this checkpoint intentionally records **no new exact pytest pass count**.

Independent review round 3 must execute exact-branch focused tests, full pytest where available, compile/import checks, checked-schema/runtime parity and `git diff --check`.

## Boundary

No KSEI network/account access, credential use, provider call, real portfolio data, public API, UI, public Ownership/KSEI changes, Financial PIT changes, Corporate Action changes, Foreign Flow changes, model changes or protected-outcome access occurred.

Next gate: independent `REVIEW_ROUND_3`; no real-auth test before acceptance.

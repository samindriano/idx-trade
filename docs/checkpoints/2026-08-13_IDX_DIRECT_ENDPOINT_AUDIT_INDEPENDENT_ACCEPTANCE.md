# Direct IDX Endpoint Discovery Audit — Independent Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Reviewed branch: `data/idx-direct-endpoint-audit-v1`
Reviewed HEAD: `52c369ae9d5ddd8fe78a8fcea7c86c83fa33f901`
Primary discovery checkpoint: `docs/checkpoints/2026-08-13_IDX_ISSUED_HISTORY_FINANCIAL_REPORT_PROBE.md`
Decision: `DIRECT_IDX_ENDPOINT_DISCOVERY_ACCEPTED_PARTIAL_SOURCE_USEFUL_NOT_PIT_READY`

## Independent review

The bounded discovery is accepted as decision-valid for its stated scope.

Verified review conclusions:

- The documented `idx-bei` transport is operational for the tested IDX endpoint families; the final pass records 14/14 HTTP 200 responses with no retry or pagination expansion.
- `GetIssuedHistory` is correctly classified as an official candidate event/share-count ledger, not as a complete or PIT-safe shares-outstanding state. The checkpoint explicitly preserves incomplete pagination, ambiguous `TanggalPencatatan` semantics, zero share-count observations, and the lack of publication/effective/knowledge timestamps.
- `GetFinancialReport` is correctly classified as useful filing discovery/provenance metadata. `File_Modified` is not promoted to publication or knowledge time, and announcement/publication cross-check remains required before PIT use.
- The prior `LINK_FINANCIAL_DATA_RATIO` sector-field path remains rejected for PIT sector history because the PALM counterexample demonstrates terminal/current classification leakage into a pre-effective financial-report row.
- No dataset/model/scoring/protected outcome/bulk backfill was changed by this lane.

## Accepted disposition

1. Direct IDX transport through the documented `idx-bei` client is a validated bounded research/discovery mechanism in this environment.
2. `GetIssuedHistory` may be retained as a candidate official corporate-action/share-count source for future separately-scoped work, but it must not be treated as a standalone continuous shares-outstanding timeline.
3. `GetFinancialReport` may be retained as a filing-discovery/provenance source, but `File_Modified` must not be interpreted as PIT publication time without independent publication evidence.
4. `LINK_FINANCIAL_DATA_RATIO` sector classifications must not be used as historical PIT sector state.
5. This discovery lane is complete. Any future bulk acquisition, canonical source promotion, event-timeline construction, or fundamental-PIT integration requires its own scope/provenance contract and coordination claim.

No remediation is required for this audit.
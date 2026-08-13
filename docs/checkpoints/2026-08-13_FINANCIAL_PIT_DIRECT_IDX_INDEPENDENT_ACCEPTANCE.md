# Financial PIT Direct IDX — Independent Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Reviewed branch: `data/financial-pit-v1`
Reviewed HEAD: `64d52dbfbe0972cd6ab555c6a9520723634689c6`
Decision: `FINANCIAL_PIT_DIRECT_IDX_SOURCE_AUDIT_ACCEPTED_PARTIAL_SOURCE_USEFUL_PIT_COVERAGE_INCOMPLETE`

## Review conclusion

The bounded direct-IDX Financial PIT publication-chain audit is accepted.

Accepted findings:

- direct `ListedCompany/GetFinancialReport` and `ListedCompany/GetAnnouncement` are reachable through the documented `idx-bei` transport for the bounded sample;
- BBCA FY2024, BBCA Q1 2025, AADI FY2024, and TLKM 9M 2025 have deterministic filing-to-announcement linkage by exact attachment filename;
- direct report bytes and announcement attachment bytes match, and the four previously preserved XLSX hashes match 4/4;
- `File_Modified` agrees with `TglPengumuman` to second precision in the bounded sample, while `CreatedDate` is demonstrably unsafe as publication time;
- issuer timestamps are naive and require an explicit `Asia/Jakarta` interpretation before UTC conversion;
- old report attachments remain discoverable when old issuer-announcement publication records are no longer exposed, so discoverability must not be promoted to PIT visibility;
- FY2022 and Q1 2023 publication linkage remains blocked, while BBCA FY2023 is still joinable through its January 2024 announcement;
- announcement pagination is non-standard enough that `ResultCount` alone cannot certify completeness;
- no immutable correction/restatement chain has been demonstrated.

## Scientific boundary

This acceptance certifies a useful direct official source family for bounded filing discovery and publication linkage where the issuer announcement is still exposed. It does **not** certify complete market-wide historical Financial PIT acquisition, revision completeness, or a 2021–2026 PIT panel.

No bulk acquisition, feature derivation, model fitting/scoring, protected-outcome access, or canonical model change is authorized by this review.

If Financial PIT is advanced later, the next implementation must be a separately bounded provenance-preserving adapter that:

1. fails closed on incomplete or ambiguous announcement results/pagination;
2. joins report to announcement deterministically;
3. interprets source timestamps explicitly as `Asia/Jakarta` and stores timezone-aware publication time;
4. derives consolidated/separate scope from parsed filing content rather than endpoint metadata;
5. preserves every raw response, attachment hash, and observed version instead of overwriting same-key conflicts;
6. keeps filings without proven announcement publication time out of PIT feature tables.

The current source-audit lane is complete and may be marked `DONE` at this accepted partial-source verdict.

# Financial PIT Offline Scope Reclassification — Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Reviewed branch: `data/financial-pit-offline-scope-reclassification-v1`
Reviewed HEAD: `45d36eda095ea975182565804baaf899a9706c58`
Decision: `FINANCIAL_PIT_OFFLINE_RECLASSIFICATION_ACCEPTED_FACT_TABLE_DESIGN_NEXT`

## Review conclusion

The offline scope reclassification and PIT-ready coverage recomputation are accepted.

Accepted evidence:

- 6,108 exact report-announcement byte joins from the previously accepted 7,370-row census were reclassified offline using the accepted statement-scope resolver;
- 4,410 rows resolve `CONSOLIDATED`, 1,555 resolve `SEPARATE`, and 143 remain `UNRESOLVED`;
- 5,965 rows satisfy the prior publication/hash gates and explicit-scope gate, equal to 97.658808% of exact joins and 80.936228% of all expected issuer-periods;
- 0 filings contain mixed/conflicting authoritative scope evidence under the accepted resolver contract;
- 140 unsupported representations remain fail-closed despite `.xlsx`-like names because their bytes are not valid XLSX ZIP packages;
- 74 ambiguous attachments, 2 hash conflicts, 28 HTTP/provider failures, 1,158 publication/attachment linkage gaps, and 143 scope-unresolved exact joins remain excluded rather than repaired or imputed;
- no provider/network calls, redownload, financial fact extraction, feature derivation, model work, canonical model mutation, or protected-outcome access occurred.

The canonical external artifacts are accepted as pinned in the reviewed checkpoint:

- rows SHA-256 `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9`;
- summary SHA-256 `6a724cc1dd4cef6fc7a9af5a4c4de1164f5e8b14d4ec38ee2887f2e75bf8ec66`;
- manifest SHA-256 `a38fdb52225da8e1c5306e1d7bb658e34e069e6920e074c59ad1f607ff01249f`.

## Independent engineering review

The reviewed classifier is fail-closed in the material paths:

- it selects the same deterministic attachment representation used by the accepted census;
- the local attachment SHA must agree with the accepted dual-source chain hash or classification aborts;
- prior chain gates require report discovery, announcement discovery, exact attachment join, publication timestamp, agreeing source hashes, and a source reference;
- `pit_ready` is emitted only when those prior gates pass and the accepted scope resolver returns an explicit non-`UNRESOLVED` scope;
- representation is inferred from file content/parser result rather than filename-only scope inference.

A previously detected aggregate mixed-scope counting error in the superseded v1 summary did not alter the per-join classification rows. The canonical v2 summary counts mixed scope per filing, and the final test explicitly guards against dataset-global cross-row mixing. The accepted final rows SHA is unchanged while the corrected summary hash is pinned separately.

## Coverage interpretation

Coverage is sufficiently high to justify the next data-engineering milestone, but it remains structurally uneven. In particular, 2024 Q1 has only 306/737 PIT-ready rows, whereas stronger periods such as 2025 H1 reach 693/737. Any later research dataset must therefore preserve period-specific eligibility and must not silently fill missing issuer-periods or assume a balanced panel.

This acceptance does not authorize treating the remaining failed rows as recoverable, nor does it authorize use of unsupported/PDF-unverified representations. The accepted 5,965 rows form the source-ready candidate set for the next milestone only.

## Authorized next milestone

A separate bounded **Financial PIT fact-table schema and extraction feasibility** milestone is authorized.

The next task should design and validate a version-aware, publication-time-preserving fact schema against a representative subset of the 5,965 accepted PIT-ready filings before any market-wide fact extraction. It must preserve at minimum issuer, fiscal period, statement scope, publication/knowledge timestamp, filing/attachment hash, statement/fact identity, units/scale, and source evidence.

Special attention is required for correction/restatement semantics: the extractor must never overwrite an earlier observed version or infer historical availability from a later replacement filing. Financial ratios/features, model training, and protected outcomes remain unauthorized until the fact-table contract and version policy are independently accepted.

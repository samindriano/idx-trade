# Financial PIT Adapter + Coverage Census — Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Reviewed branch: `data/financial-pit-adapter-census-v1`
Reviewed HEAD: `d1cb537e844fb8da83551ba462c80c8debb623d4`
Decision: `FINANCIAL_PIT_ADAPTER_CENSUS_ACCEPTED_SCOPE_RESOLUTION_NEXT`

## Review conclusion

The adapter contract and bounded 2024–2026 census are accepted.

Accepted evidence:

- 7,370 expected issuer-periods across the frozen 737-ticker census universe;
- 6,580 report rows discovered;
- 6,212 relevant announcement filename matches;
- 6,108 exact report/announcement attachment joins with matching dual-source SHA-256 bytes;
- 74 ambiguous attachment cases, 2 attachment hash conflicts, and 28 HTTP/provider failures were preserved fail-closed rather than repaired or silently dropped;
- no protected outcomes, financial feature derivation, model fit/score, or canonical model/data mutation occurred.

`PIT-ready = 0` is not evidence that the direct IDX publication chain failed. The reviewed adapter explicitly requires a validated `CONSOLIDATED` or `SEPARATE` statement scope before emitting `PIT_READY`; all 6,108 otherwise exact joins stop at `SCOPE_UNRESOLVED` because no scope resolver was supplied. This is the correct fail-closed behavior.

The current result remains `PARTIAL_SOURCE_USEFUL_PIT_COVERAGE_INCOMPLETE`: source linkage is materially useful, but no market-wide PIT financial fact table is yet authorized.

## Review of adapter boundary

The adapter correctly:

- validates `ResultCount` against returned rows and rejects incomplete pages;
- links report and issuer-announcement attachments by exact filename and verifies both attachment byte hashes;
- treats IDX naive publication timestamps as Asia/Jakarta and converts to UTC;
- does not use `CreatedDate` as publication time;
- preserves immutable raw captures and rejects conflicting logical filing hashes;
- requires explicit statement scope before PIT readiness.

One implementation choice to keep under review during the next milestone is the deterministic preference order among XLSX/XBRL/PDF representations. Scope resolution must be based on explicit filing content and must not infer scope from filename or attachment type.

## Authorized next milestone

A separate bounded **statement-scope resolution feasibility** milestone is authorized.

The next task should not rerun the 7,370-row network census and should not derive fundamentals or train models. Reuse the already captured immutable attachments and determine whether `CONSOLIDATED` versus `SEPARATE` can be extracted defensibly and version-aware from the filing contents.

Start with a representative stratified sample across:

- banks/financials and non-financial issuers;
- FY, Q1, H1, and 9M filings;
- XLSX-first filings, XBRL-available filings, and PDF-only/edge cases;
- multiple years within the accepted 2024–2026 window.

The parser must return only `CONSOLIDATED`, `SEPARATE`, or `UNRESOLVED`, preserve source evidence for the classification, and fail closed on conflicting or ambiguous filing content. No heuristic based only on filenames, issuer type, or endpoint metadata is acceptable.

Only after independent validation of scope extraction should the existing 6,108 exact joins be reclassified and a PIT-ready coverage count recomputed. Feature engineering and modeling remain unauthorized until that later gate.

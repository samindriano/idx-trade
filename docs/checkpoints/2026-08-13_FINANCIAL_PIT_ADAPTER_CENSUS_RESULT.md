# Financial PIT Direct IDX Adapter + Coverage Census

Date: 2026-08-13 (Asia/Jakarta)  
Branch: `data/financial-pit-adapter-census-v1`  
Base: accepted `data/financial-pit-v1` source audit  
Eligible-universe source SHA-256: `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe`

## Decision

The direct IDX adapter is implemented and source-readiness census is complete.
The result is:

`PARTIAL_SOURCE_USEFUL_PIT_COVERAGE_INCOMPLETE`

The source chain is useful for bounded discovery and immutable attachment
verification, but this run does not establish a PIT-ready market-wide filing
table. No financial facts, ratios, features, models, outcomes, or canonical
model/data artifacts were touched.

## Adapter contract

The new `src/idx_trade/financial_pit_adapter.py` implements:

1. `ListedCompany/GetFinancialReport` report discovery;
2. `ListedCompany/GetAnnouncement` retrieval with `ResultCount == len(Replies)`
   and duplicate-announcement rejection;
3. exact report `File_Name` to announcement `OriginalFilename`/
   `PDFFilename` matching;
4. retrieval and SHA-256 comparison of both official attachment paths;
5. explicit IDX timestamp parsing: naive source timestamps are interpreted as
   `Asia/Jakarta` and converted to UTC; `CreatedDate` is never used;
6. explicit statement-scope requirement. Without a validated
   `CONSOLIDATED`/`SEPARATE` scope, the result is `SCOPE_UNRESOLVED` and never
   `PIT_READY`;
7. immutable raw capture storage and a revision ledger that rejects conflicting
   hashes for the same logical filing and knowledge time.

The report attachment path is rooted at the IDX web origin (`/Portals/...`),
not the `/primary` API prefix. This was caught and corrected during the census.

## Bounded census

Universe: 737 eligible common-stock tickers from the accepted V3-B final
training table. Available periods as of 2026-08-13 were:

| Year | Periods | Expected issuer-periods |
|---:|---|---:|
| 2024 | Q1, H1, 9M, FY | 2,948 |
| 2025 | Q1, H1, 9M, FY | 2,948 |
| 2026 | Q1, H1 | 1,474 |
| **Total** | 10 periods | **7,370** |

`GetFinancialReport` global responses were complete for all ten requests:
the returned row count equalled `ResultCount` in each response. Announcement
responses were split into bounded date ranges until the same completeness
condition held. An unavailable response was never treated as a missing filing.

| Year | Period | Expected | Report found | Relevant announcement | Exact filename+hash join | PIT-ready | Missing publication linkage | Scope unresolved | Hash conflicts | HTTP/provider failures | Ambiguous attachment |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024 | FY | 737 | 698 | 698 | 684 | 0 | 39 | 684 | 0 | 3 | 11 |
| 2024 | Q1 | 737 | 517 | 310 | 308 | 0 | 427 | 308 | 0 | 1 | 1 |
| 2024 | H1 | 737 | 679 | 647 | 633 | 0 | 90 | 633 | 2 | 2 | 10 |
| 2024 | 9M | 737 | 651 | 651 | 641 | 0 | 86 | 641 | 0 | 1 | 9 |
| 2025 | FY | 737 | 699 | 694 | 674 | 0 | 43 | 674 | 0 | 6 | 14 |
| 2025 | Q1 | 737 | 667 | 659 | 652 | 0 | 78 | 652 | 0 | 2 | 5 |
| 2025 | H1 | 737 | 711 | 707 | 695 | 0 | 30 | 695 | 0 | 7 | 5 |
| 2025 | 9M | 737 | 682 | 580 | 572 | 0 | 157 | 572 | 0 | 4 | 4 |
| 2026 | Q1 | 737 | 669 | 668 | 662 | 0 | 69 | 662 | 0 | 0 | 6 |
| 2026 | H1 | 737 | 607 | 598 | 587 | 0 | 139 | 587 | 0 | 2 | 9 |
| **Total** |  | **7,370** | **6,580** | **6,212** | **6,108** | **0** | **1,158** | **6,108** | **2** | **28** | **74** |

Interpretation:

- `report_found=6,580`: the report inventory exposes a row matching the
  requested issuer/year/period contract;
- `announcement_found=6,212`: a relevant issuer announcement with the exact
  report filename was found;
- `exact_attachment_join=6,108`: both report and announcement attachment
  bytes were retrieved and had identical SHA-256 values;
- `PIT-ready=0`: all 6,108 successful joins remain scope-unresolved because
  the endpoint metadata does not declare consolidated versus separate and the
  census deliberately did not guess from filenames or derive scope without a
  version-aware parser;
- the two hash conflicts were preserved and excluded, not overwritten;
- 74 ambiguous filename matches and 28 attachment HTTP failures remain
  fail-closed;
- 790 report-missing plus 368 unmatched-filename cases are counted as missing
  publication linkage; they are not evidence that the report was never
  published.

## Provenance and external artifacts

Raw captures were kept outside Git under:

`D:\Documents\Project\idx-trade-financial-pit-adapter-census-20260813-v1`

Final immutable capture inventory:

- raw response files: 294;
- raw response bytes: 800,980,614;
- attachment files: 12,247;
- attachment bytes: 5,017,286,746;
- final manifest:
  `D:\Documents\Project\idx-trade-financial-pit-adapter-census-20260813-v1\MANIFEST__rerun_v6.json`;
- final manifest SHA-256:
  `e675a258e5281eb01032d6d4b73c7a94f41871b06550e2253df3b7ac7cd9946e`;
- coverage rows SHA-256:
  `dbb307fecac4eedcdf4a2d692a148c225c48fdf23fbd55c7b499cb8f275c377b`;
- period summary SHA-256:
  `7b82f48439c3d2469ef18c68a7f07682c32a8836a38a53acaec4c883684162a6`.

The manifest includes exact endpoint parameters, raw response hashes, source
attachment hashes, source references where matched, retrieval provenance, and
the eligible-universe SHA. Raw payloads and files are not committed.

## Validation and remaining blockers

- focused Financial PIT + adapter tests: **17 passed**;
- full repository pytest: **497 passed, 0 failed, 3 warnings**;
- warnings are the existing pandas `FutureWarning`s in curated identity and
  tradability reconstruction tests;
- no protected outcome path, model fit/score, financial fact derivation, or
  canonical model/data artifact was accessed.

Remaining blockers before a PIT financial fact table can be accepted:

1. version-aware extraction of explicit consolidated/separate scope from each
   filing format;
2. resolution of ambiguous/missing attachment linkage and the two conflicting
   byte pairs;
3. investigation of the 28 attachment HTTP failures without substituting an
   unapproved source;
4. a correction/restatement version policy beyond the current endpoint's one
   report row per issuer-period;
5. public announcement-history limits for older publication times.

The adapter therefore fails closed by design and is not a financial-feature or
model input producer.

# Financial PIT Offline Scope Reclassification

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/financial-pit-offline-scope-reclassification-v1`
Parent resolver: `data/financial-pit-statement-scope-v1@e4537c16c5011d8cafc55bc72e8f04017b874baf`

## Decision

The accepted statement-scope resolver was applied offline to the existing
6,108 exact report-announcement byte joins. No provider/network call,
redownload, financial fact extraction, feature derivation, model work, or
protected-outcome access occurred.

The bounded result is:

`FINANCIAL_PIT_SCOPE_RECLASSIFIED_PIT_READY_COVERAGE_INCOMPLETE`

This is a source-readiness classification, not a financial-fact dataset.

## Inputs and preservation

All input bytes remain in the accepted external census root:

`D:\Documents\Project\idx-trade-financial-pit-adapter-census-20260813-v1`

| Input | SHA-256 |
|---|---|
| `coverage_rows.jsonl` | `dbb307fecac4eedcdf4a2d692a148c225c48fdf23fbd55c7b499cb8f275c377b` |
| `MANIFEST__rerun_v6.json` | `e675a258e5281eb01032d6d4b73c7a94f41871b06550e2253df3b7ac7cd9946e` |

The resolver selected the same deterministic report attachment used by the
accepted census, asserted that its local SHA matched both accepted chain
hashes, and recorded the exact attachment-relative path, publication
timestamp, source reference, representation, scope, and evidence location /
kind for every join.

The canonical derived artifacts are external and are not committed:

`D:\Documents\Project\idx-trade-financial-pit-scope-reclassification-20260813-v2`

| Artifact | SHA-256 |
|---|---|
| `scope_reclassification_rows.jsonl` (6,108 rows) | `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9` |
| `scope_reclassification_summary.json` | `d1cb01448361b2f95236eba49440d78dbd9cc89dda1280b2fea0a379ccc6a974` |
| `MANIFEST.json` | `a38fdb52225da8e1c5306e1d7bb658e34e069e6920e074c59ad1f607ff01249f` |

The earlier `...-v1` output contains the same per-join rows but its aggregate
mixed-scope count was superseded after a focused test caught a dataset-global
counting bug. The `...-v2` summary/manifest above is the canonical result.

## Overall classification

| Measure | Count |
|---|---:|
| Total expected issuer-periods | 7,370 |
| Exact report-announcement byte joins | 6,108 |
| `CONSOLIDATED` | 4,410 |
| `SEPARATE` | 1,555 |
| `UNRESOLVED` | 143 |
| Mixed/conflicting authoritative scope | 0 |
| Recognized XLSX | 5,966 |
| Recognized XBRL ZIP | 2 |
| Recognized PDF | 0 |
| Unsupported representation | 140 |
| PIT-ready | 5,965 |
| PIT-ready / exact joins | 97.658808% |
| PIT-ready / all expected issuer-periods | 80.936228% |

The 140 unsupported representations have `.xlsx`-like source names but their
captured bytes are not valid XLSX ZIP packages, so they remain fail-closed
unsupported rather than being inferred from filenames. The two XBRL records
were resolved only through the exact accepted IDX-DEI concept and proven
`CurrentYearInstant` context contract. No PDF bytes were available in the
accepted capture root.

## Coverage by year and period

`PIT-ready %` is measured against all 737 expected eligible issuer-periods in
that year/period, not merely against the successful exact joins.

| Year | Period | Expected | Exact joins | Consolidated | Separate | Unresolved | Mixed/conflict | PIT-ready | PIT-ready % |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024 | FY | 737 | 684 | 485 | 176 | 23 | 0 | 661 | 89.687924% |
| 2024 | Q1 | 737 | 308 | 230 | 76 | 2 | 0 | 306 | 41.519674% |
| 2024 | H1 | 737 | 633 | 425 | 163 | 45 | 0 | 588 | 79.782904% |
| 2024 | 9M | 737 | 641 | 456 | 164 | 21 | 0 | 620 | 84.124830% |
| 2025 | FY | 737 | 674 | 496 | 178 | 0 | 0 | 674 | 91.451832% |
| 2025 | Q1 | 737 | 652 | 451 | 151 | 50 | 0 | 602 | 81.682497% |
| 2025 | H1 | 737 | 695 | 511 | 182 | 2 | 0 | 693 | 94.029851% |
| 2025 | 9M | 737 | 572 | 430 | 142 | 0 | 0 | 572 | 77.611940% |
| 2026 | Q1 | 737 | 662 | 494 | 168 | 0 | 0 | 662 | 89.823609% |
| 2026 | H1 | 737 | 587 | 432 | 155 | 0 | 0 | 587 | 79.647218% |

## Explicitly excluded from PIT-ready

The following remain outside the PIT-ready set and were not repaired:

- 74 `ATTACHMENT_AMBIGUOUS` rows;
- 2 `ATTACHMENT_HASH_CONFLICT` rows;
- 28 `HTTP_FAILURE` rows;
- 1,158 publication/attachment linkage gaps (`REPORT_NOT_FOUND` or
  `ATTACHMENT_NOT_MATCHED`);
- 143 exact joins whose content resolver returned `UNRESOLVED`.

The counts sum to the 7,370 expected issuer-periods. No missing value was
converted into a valid-looking scope or publication timestamp.

## Validation and next boundary

- Focused resolver + reclassification tests: **14 passed, 0 failed**.
- Full repository pytest: pending final run after this checkpoint's code/test
  changes.
- `git diff --check`: pending final run.

The next step requires independent ChatGPT review of this offline coverage
result. No financial facts/features or model input may consume the PIT-ready
rows until the unresolved/unsupported and prior publication-chain blockers are
separately accepted.

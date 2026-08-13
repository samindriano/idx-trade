# Financial PIT Market-Wide Offline Fact-Extraction Census

**Date:** 2026-08-13
**Branch:** `data/financial-pit-marketwide-fact-extraction-census-v1`
**Status:** `MARKETWIDE_OFFLINE_CENSUS_COMPLETE_FEATURE_DESIGN_REVIEW_REQUIRED`

## Scope and authorization

This run applies the accepted hardened extractor from
`data/financial-pit-fact-extraction-hardening-v1@baf0334a1dd6a31e9d88ae978630ec864bfb3410`
to all 5,965 already accepted PIT-ready XLSX/XBRL joins. It is an extraction
and coverage census only.

No provider/network calls, redownloads, ratios, growth calculations,
fundamental features, model work, or protected-outcome access occurred. Missing
facts remain missing. The accepted observed-version policy remains in force:
an observed filing version is usable only from its own proven publication
timestamp; an unavailable earlier version is not backfilled.

The immutable source rows were verified before parsing:

- total exact joins: **6,108**;
- source rows SHA-256:
  `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9`;
- processed PIT-ready rows: **5,965**;
- source format: **5,963 XLSX + 2 XBRL**;
- scope: **4,410 CONSOLIDATED + 1,555 SEPARATE**.

The 143 non-PIT-ready scope-unresolved joins were excluded. Earlier census
failures outside the 6,108 exact-join input—unsupported representations,
ambiguous attachments, hash conflicts, provider failures, and publication or
linkage gaps—were not repaired or reintroduced.

## Corpus and extraction status

The run produced **22,041** fact candidates. **21,962** were extracted
(99.6416% of candidates); the remainder stayed explicit diagnostics:

| Status | Count | Treatment |
|---|---:|---|
| `EXTRACTED` | 21,962 | Explicit label/QName, current context, unit/scale and provenance passed |
| `UNRESOLVED_UNIT` | 64 | ASII filing presentation currency/scale metadata remains unresolved |
| `UNRESOLVED_PERIOD` | 15 | Prior-period XBRL contexts remain rejected |
| `UNRESOLVED_TAXONOMY` | 0 | No market-wide XBRL taxonomy failure in this corpus |
| `CONFLICTING_FACTS` | 0 | No unresolved same-priority fact conflict |

Format status:

- XLSX: 5,963 filings; 21,953 extracted and 64 unresolved-unit candidates;
- XBRL: 2 filings; 9 extracted and 15 unresolved-period candidates.

Template/industry families:

- GENERAL: 5,571;
- FINANCIAL_SHARIA: 392;
- XBRL taxonomy family not used as an XLSX template class: 2.

## Core-fact coverage

Coverage denominator is all 5,965 PIT-ready filings. A missing fact is not
counted as zero and is not inferred from another statement.

| Core fact | Extracted | Unresolved | Missing | Coverage |
|---|---:|---:|---:|---:|
| revenue | 2,415 | 9 | 3,542 | 40.4862% |
| net income | 2,965 | 10 | 2,990 | 49.7066% |
| net income attributable | 2,979 | 10 | 2,978 | 49.9413% |
| total assets | 2,475 | 10 | 3,482 | 41.4920% |
| total liabilities | 2,622 | 10 | 3,334 | 43.9564% |
| total equity | 2,646 | 10 | 3,310 | 44.3588% |
| cash and cash equivalents | 2,575 | 10 | 3,382 | 43.1685% |
| cash (distinct exact label) | 341 | 0 | 5,624 | 5.7167% |
| operating cash flow | 2,944 | 10 | 3,011 | 49.3546% |

The unresolved column includes the 8 ASII filing-level unit diagnostics for
each applicable core label and the 1–2 rejected prior-period XBRL observations.

Coverage is also persisted without aggregation loss in external
`coverage.json`, keyed by year, period, scope, template/industry family and
representation format.

## Year/period coverage

The following is candidate-level extraction coverage across all core fact
identities for each filing-period block. Exact per-fact values remain in
`coverage.json`.

| Year/period | Filings | Candidates | Extracted | Candidate extraction |
|---|---:|---:|---:|---:|
| 2024 FY | 661 | 4,053 | 4,045 | 99.80% |
| 2024 Q1 | 306 | 1,899 | 1,899 | 100.00% |
| 2024 H1 | 588 | 3,669 | 3,653 | 99.56% |
| 2024 9M | 620 | 3,836 | 3,828 | 99.79% |
| 2025 FY | 674 | 939 | 931 | 99.15% |
| 2025 Q1 | 602 | 3,660 | 3,652 | 99.78% |
| 2025 H1 | 693 | 1,254 | 1,246 | 99.36% |
| 2025 9M | 572 | 785 | 785 | 100.00% |
| 2026 Q1 | 662 | 1,072 | 1,064 | 99.25% |
| 2026 H1 | 587 | 874 | 859 | 98.28% |

## Scope and provenance dimensions

Exact filing counts are:

- GENERAL / CONSOLIDATED: 4,226;
- GENERAL / SEPARATE: 1,345;
- FINANCIAL_SHARIA / CONSOLIDATED: 183;
- FINANCIAL_SHARIA / SEPARATE: 209;
- XBRL / explicit-taxonomy family: 2 (one consolidated, one separate).

Every fact record retains ticker, fiscal year/period, statement scope,
publication and knowledge timestamp, version ID, attachment SHA, source
reference, statement/fact identity, raw value, currency/unit/scale, fiscal
context, taxonomy/version, exact source locator, extraction status and detail.
Every diagnostic also retains the source-row evidence, source-chain hashes,
and chain-gate flags.

## Decision

**Census verdict:** `CONDITIONAL_GO_FOR_SEPARATE_FEATURE_DESIGN_REVIEW`.

The extraction mechanics are reliable enough to start a separately reviewed
feature-design phase with explicit missingness and scope contracts. This is not
a complete dense fundamental panel: the core facts are present in roughly
40–50% of eligible filings, the exact `cash` label is sparse, and 64 unit
diagnostics remain fail-closed. Any feature-design work must decide whether
the distinct `cash` and `cash_and_cash_equivalents` concepts can be combined
without semantic loss, and must not derive ratios or features until separately
authorized.

The result is **not** a license for market-wide feature materialization,
modeling, or outcome work. A separate feature-design specification and review
are required.

## External artifacts

Final external root:

`D:\Documents\Project\idx-financial-pit-marketwide-fact-extraction-census-20260813-v1-final-v2`

- `fact_records.jsonl`: `4e73eb0cce07b0bfb4d9cc12a4ecb6b54eba697a2e327ef6316b32acbdea3a42`
- `filing_diagnostics.jsonl`: `a38bd9489b527430e967018cdb146989960f13c0b343c95504612fa19bfdfb1d`
- `coverage.json`: `adaab5e3cc6537cfa2e45f130ebc31452489c9b641c374b33c6f98f02ca17d3c`
- `exclusions.json`: `209e9f2b2c8543b46c66023e5d29162d5db84dbfa7d86ee798388d07a4c7ec4c`
- `summary.json`: `429f2d39c44b51396ca8f263800946ddfded9f4d8f77d1a2f336f25a0f9ccdd0`
- `MANIFEST.json`: `e85469a52f749ab72869716b2689cfb2005e222103e2bfc7fdec1de4264eb872`

The manifest pins the accepted extractor commit and input-row SHA. Raw
attachments remain outside Git.

## Validation

- focused census + fact tests: **14 passed**;
- full repository pytest: **515 passed, 0 failed, 3 existing warnings**;
- `git diff --check`: passed.

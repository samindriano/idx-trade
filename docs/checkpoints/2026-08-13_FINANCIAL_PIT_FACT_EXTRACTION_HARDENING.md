# Financial PIT Fact-Extraction Hardening

**Date:** 2026-08-13
**Branch:** `data/financial-pit-fact-extraction-hardening-v1`
**Status:** `BOUNDED_SAMPLE_HARDENED_MARKET_WIDE_EXTRACTION_BLOCKED`

## Scope and boundaries

This was an offline hardening run only. It reused the immutable attachments
from the accepted Financial PIT census and did not make provider calls,
redownload files, extract market-wide facts, derive ratios/features, train or
score a model, or access protected outcomes.

Inputs:

- accepted 36-filing sample from `data/financial-pit-fact-schema-v1`;
- reclassification rows:
  `D:\Documents\Project\idx-trade-financial-pit-scope-reclassification-20260813-v2\scope_reclassification_rows.jsonl`;
- immutable attachments:
  `D:\Documents\Project\idx-trade-financial-pit-adapter-census-20260813-v1`;
- reclassification-row SHA-256:
  `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9`.

## Hardening implemented

### XLSX currency/unit/scale

The resolver now reads reporting currency and scale only from the visible IDX
presentation metadata block (`1000000`), using the explicit reporting-currency
and rounding/scale labels. It no longer treats statement-body `IDR`, `AS$`,
narrative text, or breakdown rows as filing-level presentation semantics.
Missing or unrecognized metadata remains `UNRESOLVED_UNIT`.

### Repeated labels

Candidate facts are grouped by statement role and current-period context. The
operating-cash-flow mapping gives the explicit final net-operating-cash-flow
labels higher authority than the intermediate “cash from operations” subtotal.
The selected location and discarded lower-priority candidates are recorded in
the fact detail. Equivalent duplicates are deterministic; conflicting
same-priority values or contexts remain `CONFLICTING_FACTS`.

### XBRL taxonomy, unit and context

XBRL facts require the exact accepted `idx-cor` concept, an official IDX COR
taxonomy namespace, an internally consistent taxonomy version, an ISO currency
`unitRef`, an integer `scale`, and `CurrentYearInstant` or
`CurrentYearDuration`. A `schemaRef`, when present, must identify the same
official IDX taxonomy version; an official namespace may establish the version
when the inline package omits `schemaRef`. Missing/conflicting taxonomy or
schema metadata is represented as `UNRESOLVED_TAXONOMY`; invalid unit/scale is
`UNRESOLVED_UNIT`; invalid period context remains `UNRESOLVED_PERIOD`.

## Existing 36-filing sample: before vs after

The 212 candidate observations and the 15 invalid-period diagnostics are
unchanged. The previous accepted sample was:

| Status | Before | After | Change |
|---|---:|---:|---:|
| `EXTRACTED` | 141 | 197 | +56 |
| `UNRESOLVED_UNIT` | 42 | 0 | -42 |
| `CONFLICTING_FACTS` | 14 | 0 | -14 |
| `UNRESOLVED_PERIOD` | 15 | 15 | unchanged |

Therefore all 42 former unit/scale cases and all 14 former repeated-label
conflicts became safely extractable in this bounded sample. The 14 conflict
cases were the known operating-cash-flow subtotal/final-total collisions; the
final total was selected only by explicit label authority, not by first-match
order. No old ambiguity was silently reclassified as a value.

The two real XBRL samples (UNTD 2024 H1 and VTNY 2026 H1) resolved their
official namespace-derived taxonomy version as `2020-01-01`. Their prior-year
contexts remain rejected, so the XBRL result is not a claim that all contexts
are usable.

## Targeted adversarial sample

Six new focused adversarial tests cover:

- presentation metadata overriding body/narrative currency text;
- authoritative OCF total overriding a lower-priority subtotal;
- conflicting same-priority OCF totals remaining fail-closed;
- official IDX namespace without `schemaRef`;
- missing taxonomy and namespace/schemaRef version conflict;
- invalid XBRL unit or scale.

The full fact-table test module passed **13 tests** after these additions.

## Artifacts

The final offline sample artifacts are outside Git at:

`D:\Documents\Project\idx-financial-pit-fact-extraction-hardening-20260813-v1-run1`

Actual file SHA-256 values:

- `sample_selection.json`: `de7381c595b09044c1760e5e4298ea883427576125a6f9cfdd5a06648d559abe`
- `fact_records.jsonl`: `d56415c65148141d4e571ab7d0c9b25e436a0548ce22de90242dc47f29c2d512`
- `filing_diagnostics.jsonl`: `c29792a51deeef71c939b14328dccdd7fd8b660009764f07e11a57e74f0537c6`
- `summary.json`: `2f72cebdcfe902bf1b14b5ee5f8c259b92d893f83a75ed1df5d76fdd243d80a9`
- `MANIFEST.json`: `9cb0f5797145921a8871b21542afa7604343efec5450ef8dea41967764ecdabb`

## Validation and decision

- focused fact-table tests: **13 passed**;
- full repository pytest: **514 passed, 0 failed, 3 warnings**;
- `git diff --check`: passed.

The hardening result is accepted for the bounded sample, but the market-wide
fact table remains **NOT YET DEFENSIBLE**. The 36 filings do not establish
market-wide correction/version completeness, unsupported/PDF policy, or full
taxonomy and context coverage. No market-wide extraction is authorized by this
checkpoint.

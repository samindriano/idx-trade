# Financial PIT Fact-Table Schema Feasibility

**Date:** 2026-08-13
**Branch:** `data/financial-pit-fact-schema-v1`
**Status:** `BOUNDED_SCHEMA_FEASIBILITY_GO_MARKET_WIDE_EXTRACTION_BLOCKED`

## Scope and source boundary

This checkpoint records one offline feasibility run. It did not make provider
calls, redownload attachments, perform market-wide extraction, derive ratios or
features, train a model, or access protected outcomes.

The accepted input was the 5,965 PIT-ready exact report/announcement/attachment
joins from the offline scope reclassification lane:

- rows: `D:\Documents\Project\idx-trade-financial-pit-scope-reclassification-20260813-v2\scope_reclassification_rows.jsonl`
- rows SHA-256: `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9`
- accepted scope-reclassification manifest SHA-256:
  `a38fdb52225da8e1c5306e1d7bb658e34e069e6920e074c59ad1f607ff01249f`
- accepted count: 5,965 / 6,108 exact joins
- accepted representations: 5,963 XLSX plus 2 XBRL

The sample reused the immutable attachment bytes already held in the accepted
census root. No raw bytes were copied into Git or the repository.

## Version-aware schema

The prototype adds `src/idx_trade/financial_fact_table.py` and keeps filing
versions append-only. A fact carries, at minimum:

- issuer/fiscal identity: ticker, fiscal year, raw period (`audit`, `tw1`,
  `tw2`, `tw3`), statement scope;
- time/provenance: `publication_at_utc`, `knowledge_at_utc`, attachment SHA,
  source reference, representation format, immutable `version_id`;
- statement/fact identity: statement role, canonical fact identity, raw label
  or QName, taxonomy and taxonomy-version field;
- numeric semantics: value, currency/unit, scale, context-derived instant vs
  duration period descriptor;
- evidence: exact XLSX sheet/cell or XBRL member/element/context locator,
  evidence kind, extraction status and detail.

`version_id = SHA256(ticker|fiscal_year|fiscal_period|publication_at_utc|attachment_sha256)`.
Appending a later version preserves the earlier row. Appending a different
attachment hash for the same logical fact and knowledge timestamp fails closed.
The extractor never creates a standalone quarter from `tw2`/`tw3`; the source
context and raw reporting period are preserved.

## Stratified sample

The deterministic sample contains **36 filings**:

| Dimension | Count |
|---|---:|
| XLSX / XBRL | 34 / 2 |
| CONSOLIDATED / SEPARATE | 19 / 17 |
| Financial/Sharia XLSX | 18 |
| General Industry XLSX | 16 |
| 2024 / 2025 / 2026 | 16 / 16 / 4 |
| XBRL 2024 H1 / XBRL 2026 H1 | 1 / 1 |

The sample spans FY, Q1, H1 and 9M source periods. Financial/non-financial
classification is based on the visible IDX statement-template taxonomy, not a
ticker-name guess.

## Extraction result

The sample produced **212 candidate fact observations**:

| Status | Count | Interpretation |
|---|---:|---|
| `EXTRACTED` | 141 | exact label/QName, target context, explicit unit/scale, and evidence locator passed |
| `UNRESOLVED_UNIT` | 42 | candidate value exists but explicit presentation currency/scale conflicts or is not safely resolved |
| `CONFLICTING_FACTS` | 14 | repeated exact candidate labels yielded more than one current-period value; no value selected |
| `UNRESOLVED_PERIOD` | 15 | XBRL candidate is a prior-period context and is not used for the target filing period |

The extracted fraction of candidate observations was **141 / 212 = 66.5094%**.
By canonical identity, extracted counts were: cash 13; cash and cash
equivalents 10; net income 21; attributable net income 23; operating cash flow
10; revenue 9; total assets 19; total equity 18; total liabilities 18. The
remaining candidate identities are explicitly listed in the external
diagnostics rather than imputed.

The successful rows cover the requested core concepts where the source was
explicit: revenue, net income, attributable net income, total assets,
liabilities, equity, cash/cash equivalents and operating cash flow. Missing
facts are retained in per-filing diagnostics; absence is not converted into
zero. Shares/equity-related facts were not promoted because their semantics
were not part of this bounded canonical mapping.

### Evidence patterns

- **XLSX:** visible `1000000` metadata supplies the bilingual scope marker
  (`B20`), reporting currency (`B29`) and scale/rounding (`B31`) where present.
  Primary statement labels and values are read only from statement-role sheets
  and the explicit `CurrentYearInstant`/`CurrentYearDuration` header. Hidden
  sheets are excluded through workbook relationships and visibility state.
- **XBRL:** only exact `idx-cor` concepts are accepted. The parser retains
  QName, member, element ordinal, `contextRef`, `unitRef`, `scale`, and period
  kind. Only `CurrentYearInstant` or `CurrentYearDuration` is eligible for the
  target observation. Prior-year contexts are retained as rejected diagnostics.

### Unit/scale and taxonomy findings

XLSX is structurally usable but not uniform. Some files make IDR/full-unit or
IDR-million semantics explicit; representative AADI and some ACRO periods also
expose conflicting currency/scale text, so those candidate facts remain
`UNRESOLVED_UNIT`. Financial/Sharia and General Industry use different
statement-sheet families and cannot share sheet-number assumptions.

The XBRL sample used `unitRef=IDR` and `scale=0` on accepted facts, but the
sample did not expose a complete explicit `<unit>` definition/taxonomy-version
chain. The prototype therefore records `IDX_COR` while leaving
`taxonomy_version=UNRESOLVED_SCHEMA_REF` when the package does not provide a
usable schema reference. This is an audit blocker, not a guessed promotion.

Repeated labels also occur in breakdown/narrative content. The prototype
fail-closes when the same canonical label has multiple current-period values;
it does not choose the first or largest value. Operating-cash-flow conflicts
were observed in several XLSX filings for this reason.

## Correction/restatement/version semantics

The accepted census preserves attachment and publication-chain hashes, but it
contains one selected attachment/version per accepted logical period; it is not
a complete revision history. The source audit found three accepted correction
markers (RONY FY2024 `KOREKSI`, BAPA FY2025 `REVISI`, MUTU H1-2025 `KOREKSI`).
Those prove corrected filing events exist, but do not prove that prior versions
are retained or that supersession is complete. The prototype therefore keeps
each observed `(publication_at, attachment_sha)` as a separate version and
does not infer an earlier knowledge timestamp from a later replacement.

The following remain outside the accepted set and were not repaired here:
1,158 publication/attachment linkage gaps, 74 ambiguous attachments, 2 hash
conflicts, 28 HTTP/provider failures, 790 report-not-found cases and 140
unsupported representations. No PDF bytes were available in the accepted
capture root.

## Decision

**Schema/extraction prototype:** `GO` for further bounded offline work.  The
schema is sufficiently explicit to preserve provenance and reject ambiguity.

**Market-wide immutable fact table:** `NO-GO / NOT_YET_DEFENSIBLE`.

Market-wide extraction remains blocked until a separate bounded gate establishes
complete correction/restatement lineage, a policy for unsupported/PDF filings,
explicit unit/scale semantics across the required taxonomy families, and
complete period-context/taxonomy-version handling. No market-wide extraction
was run in this task.

## Artifacts

External audit artifacts (not committed) are under:
`D:\Documents\Project\idx-trade-financial-pit-fact-schema-20260813-v1`

- `sample_selection.json` SHA-256:
  `de7381c595b09044c1760e5e4298ea883427576125a6f9cfdd5a06648d559abe`
- `fact_records.jsonl` SHA-256:
  `6e4eb9cabffd5352e98fc966201b4ec4860991565a363baba54999d8cf593d54`
- `filing_diagnostics.jsonl` SHA-256:
  `41d25abd0aeccbbb4a5d8bd28db3ef670b9cce0968e431341c2e572c9d2fc130`
- `summary.json` SHA-256:
  `e3e9c3aeb40e0bffefaa800872e4aaaca5ec645d43f9c4f09d5ad44c7ee0e8ec`
- `MANIFEST.json` SHA-256:
  `6fb43ae8a4df62aab5a63faa4729e193f58c5efcc54cbea4ef3dc4e82e539b5f`

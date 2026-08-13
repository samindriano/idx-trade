# Financial PIT Statement-Scope Feasibility

Date: 2026-08-13 (Asia/Jakarta)

Status: `BOUNDED_SCOPE_RESOLVER_READY_REVIEW`

## Authorization and boundaries

This milestone follows the accepted adapter census at
`review/idx-financial-pit-adapter-census-acceptance-v1@723200c32e06d99831b8ea43700fe695c397e4a0`.
It reuses only the immutable captured attachment root
`D:\Documents\Project\idx-trade-financial-pit-adapter-census-20260813-v1`.

No network request, attachment redownload, 7,370-row census rerun, financial
fact extraction, ratio/feature derivation, model work, protected outcome
access, or canonical PIT coverage recomputation was performed.

## Sample and source inventory

The attachment directory contains 12,243 XLSX files and four XBRL ZIP
representations. It contains no captured PDF bytes. The raw IDX report payloads
list PDF attachments, but inspecting those would require a new attachment
download and was outside this bounded task.

The manually verified sample contains 11 captured representations:

| issuer class | periods/years | format | sample count | result |
|---|---|---:|---:|---|
| banks/financials: BBCA | FY 2024, Q1 2025, Q1 2026 | XLSX | 3 | all `CONSOLIDATED` |
| non-financial: AADI, ADRO, TLKM | FY 2024, H1 2025, 9M 2025 | XLSX | 3 | all `CONSOLIDATED` |
| non-financial: ADES, ACRO | FY 2024, Q1 2026 | XLSX | 3 | all `SEPARATE` |
| non-financial: UNTD, VTNY | H1 2024, H1 2026 | XBRL ZIP | 2 | `SEPARATE`, `CONSOLIDATED` |

Manual content inspection and the resolver agreed on all 11 classifications
(11/11). No selected filing exposed conflicting visible scope markers.

Representative source hashes and evidence locations are preserved below so
the result is auditable without committing the external attachments:

| ticker | period | representation | result | source SHA-256 | authoritative location/evidence |
|---|---|---|---|---|---|
| BBCA | FY 2024 | XLSX | CONSOLIDATED | `0fb2f5ae05e4a9b90f593500ad251260d21d2e4cf0d2b5e4280da2d335d05126` | visible `sheet=1000000;cell=B20`: `Entitas grup / Group entity` |
| BBCA | Q1 2025 | XLSX | CONSOLIDATED | `6500e5683e981aee063bb5ae752bb147725f8d1a2148a09c9e698691381922bb` | visible `sheet=1000000;cell=B20`: `Entitas grup / Group entity` |
| BBCA | Q1 2026 | XLSX | CONSOLIDATED | `055ad5072b7d16379f144657971f9221aac5b6925244e95aeb4ff16c9d66b0e7` | visible `sheet=1000000;cell=B20`: `Entitas grup / Group entity` |
| AADI | FY 2024 | XLSX | CONSOLIDATED | `b6ff2117193410503510c154190f02e5530fb8cc7524368a09ba811b58bd5642` | visible `sheet=1000000;cell=B20`: `Entitas grup / Group entity` |
| ADRO | H1 2025 | XLSX | CONSOLIDATED | `4030bc7965698ff2b1f99c93ba86fed0709c84a17c40e77371d61c56abd4e3d5` | visible `sheet=1000000;cell=B20`: `Entitas grup / Group entity` |
| TLKM | 9M 2025 | XLSX | CONSOLIDATED | `65ffef8eecf97b2e5bddca5a3047d1e62308be1244525c48b92d9958aad03ff3` | visible `sheet=1000000;cell=B20`: `Entitas grup / Group entity` |
| ADES | FY 2024 | XLSX | SEPARATE | `9e8d4db9d93c000848ba05ff202f46845a55ce694b025782a928e90a16e90286` | visible `sheet=1000000;cell=B20`: `Entitas tunggal / Single entity` |
| ADES | Q1 2026 | XLSX | SEPARATE | `744807b80de6ddf12484e1b5c5d718d8d97c7d649a18dda70c002428118cbf0a` | visible `sheet=1000000;cell=B20`: `Entitas tunggal / Single entity` |
| ACRO | FY 2024 | XLSX | SEPARATE | `6b3a66da527829eb5389d639ef7e0d49cdc29bcf719c6ccc7c4b0fdf3cabebb3` | visible `sheet=1000000;cell=B20`: `Entitas tunggal / Single entity` |
| UNTD | H1 2024 | XBRL ZIP | SEPARATE | `d60ee439d5b16d98ee9343a73ddd4c461eaed9d10e855834ad657320e08f3bb7` | `1000000.html`, `idx-dei:WhetherTheFinancialStatementsAreOfAnIndividualEntityOrAGroupOfEntities`, `contextRef=CurrentYearInstant`, value `Entitas tunggal / Single entity` |
| VTNY | H1 2026 | XBRL ZIP | CONSOLIDATED | `866c3da65f6ac587831c5ff087c5b5bc821d846461cf2b16f47657a01e4114e4` | `1000000.html`, same IDX-DEI concept, `contextRef=CurrentYearInstant`, value `Entitas grup / Group entity` |

## Granularity finding

For this bounded sample, `CONSOLIDATED` versus `SEPARATE` is an explicit
filing-level selector in the submitted IDX representation. The XLSX files
contain a visible selector in `1000000!B20`; the same files also contain a
hidden template sheet with both possible labels. The hidden template options
are not statement facts and are intentionally ignored. Inline XBRL exposes the
same decision as a non-numeric IDX-DEI concept with an explicit context and
selected value.

This sample therefore supports a filing-level resolver for the current
bounded source. It does **not** prove that every future IDX representation can
never contain both scopes. If both authoritative visible/XBRL/PDF markers are
found in one filing, the resolver returns `UNRESOLVED`; the existing singular
filing `statement_scope` field must then be replaced or supplemented by
statement/fact-level scope before that filing can become PIT-ready.

## Resolver contract

`src/idx_trade/financial_scope_resolver.py` returns only:

- `CONSOLIDATED` when one explicit content-level scope is found;
- `SEPARATE` when one explicit content-level scope is found;
- `UNRESOLVED` for missing, malformed, mixed, or conflicting evidence.

Filename, issuer type, report period, endpoint metadata, and hidden XLSX
template options never determine the result. XLSX visible labels, XBRL
concept/context/value evidence, and PDF statement titles are retained with
location, evidence kind, text, and source SHA-256.

The existing adapter does not need an immediate schema refactor for the
bounded sample. It must call this resolver and pass a scope only when the
result is explicit. A mixed-scope filing remains a hard stop and is the
trigger for a future statement/fact-level adapter revision; this milestone
does not reclassify the 6,108 exact joins or claim any PIT-ready count.

## Validation

- focused resolver tests: `6 passed`;
- direct resolver inspection of the 11 immutable sample attachments: `11/11`
  manually verified classifications;
- no network or raw attachment mutation;
- no financial facts, ratios, features, models, or protected outcomes.

## Decision

`CONDITIONAL_FILING_LEVEL_SCOPE_RESOLVER_READY`

The bounded evidence supports a filing-level resolver, with fail-closed
handling for any mixed or ambiguous future filing. PDF coverage remains an
explicit evidence gap because the existing immutable capture contains report
metadata for PDFs but no PDF bytes. Market-wide scope reclassification and
PIT coverage recomputation require a separately reviewed next task.

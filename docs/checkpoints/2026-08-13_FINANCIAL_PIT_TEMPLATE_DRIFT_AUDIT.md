# Financial PIT Missing-Fact / Template-Drift Audit

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/financial-pit-template-drift-audit-v1`
Status: `TEMPLATE_SERIALIZATION_DRIFT_CONFIRMED_EXACT_LABELS_RETAINED`

## Scope and boundaries

This is an offline audit of the accepted market-wide census. It reused only:

- 6,108 exact scope-reclassification joins, source SHA-256
  `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9`;
- 5,965 accepted PIT-ready filings;
- existing immutable XLSX/XBRL attachments;
- accepted census `MANIFEST.json`, SHA-256
  `e85469a52f749ab72869716b2689cfb2005e222103e2bfc7fdec1de4264eb872`.

No network/provider call, redownload, ratio/feature derivation, model work, or
protected-outcome access occurred. The accepted census and canonical extractor
were not modified. The audit uses only exact existing `FACT_LABELS`, exact
statement/current-period context, visible workbook sheets, and a strict ASCII
decimal/scientific-notation decoder. It adds no fuzzy or guessed mappings.

External result root:
`D:\Documents\Project\idx-financial-pit-template-drift-audit-20260813-v1-run3`

## Finding

The candidate-density collapse is primarily a serialization/template drift,
not a broad loss of semantic labels. In representative and full-corpus
inspection, labels such as `Jumlah aset`, `Jumlah liabilitas`, `Jumlah ekuitas`,
`Kas dan setara kas`, `Penjualan dan pendapatan usaha`, and the authoritative
operating-cash-flow labels remain present with the same exact normalized text
and current-period contexts.

From H1-2025 onward, many current-period value cells are serialized as
scientific notation such as `1.4002934741E10` or `2.62726760367E11`. The accepted
parser's decimal grammar rejects exponent notation, so these rows disappear
before becoming fact candidates. The independent XML audit found the following
scientific-notation value-cell counts:

| Period | Scientific-notation value cells |
|---|---:|
| 2024 Q1 | 9 |
| 2025 Q1 | 109 |
| 2025 H1 | 3,420 |
| 2025 9M | 3,098 |
| 2025 FY | 3,608 |
| 2026 Q1 | 3,391 |
| 2026 H1 | 3,048 |

Hidden/veryHidden workbook-sheet duplication is a secondary structural drift.
The canonical extractor correctly excludes hidden sheets. Hidden core-label or
context occurrences increased from 112 in 2025 Q1 to 6,629 in 2025 H1 in the
independent audit, but representative hidden copies did not supply a separate
valid current-period numeric value. They must remain excluded from evidence.

## Coverage: accepted parser versus audit-effective exact values

The audit does not promote values into the canonical fact table. “Audit-
effective” means an exact canonical label and current-period numeric value was
found, with no authoritative conflict and explicit unit/scale evidence; it is
the count that a future separately reviewed extractor change could potentially
consider.

The two XBRL rows were kept outside the XLSX drift computation and remain under
the accepted XBRL statuses. The table below covers 5,963 XLSX filings.

| Core fact | Parser extracted | Audit-effective | Strictly recoverable drift | Effective coverage |
|---|---:|---:|---:|---:|
| revenue | 2,414 | 4,291 | 1,877 | 71.96% |
| net income | 2,965 | 4,696 | 1,731 | 78.75% |
| attributable net income | 2,977 | 4,696 | 1,719 | 78.75% |
| total assets | 2,473 | 4,696 | 2,223 | 78.75% |
| total liabilities | 2,621 | 4,696 | 2,075 | 78.75% |
| total equity | 2,645 | 4,696 | 2,051 | 78.75% |
| cash and cash equivalents | 2,573 | 4,304 | 1,731 | 72.18% |
| exact `cash` | 341 | 392 | 51 | 6.57% |
| operating cash flow | 2,944 | 4,691 | 1,747 | 78.67% |

The remaining gaps are not automatically repairable: absent exact labels,
missing current-period numeric cells, unresolved unit metadata, and
authoritative conflicts remain missing/fail-closed.

## Period-level candidate density and effective coverage

| Period | Filings | Parser candidates | Strict drift recoveries | Effective candidates | Effective / all core slots |
|---|---:|---:|---:|---:|---:|
| 2024 FY | 661 | 4,045 | 70 | 4,115 | 69.17% |
| 2024 Q1 | 306 | 1,899 | 8 | 1,907 | 69.24% |
| 2024 H1 | 587 | 3,648 | 24 | 3,672 | 69.51% |
| 2024 9M | 620 | 3,828 | 15 | 3,843 | 68.87% |
| 2025 FY | 674 | 931 | 3,265 | 4,196 | 69.17% |
| 2025 Q1 | 602 | 3,652 | 98 | 3,750 | 69.21% |
| 2025 H1 | 693 | 1,246 | 3,093 | 4,339 | 69.57% |
| 2025 9M | 572 | 785 | 2,800 | 3,585 | 69.64% |
| 2026 Q1 | 662 | 1,064 | 3,071 | 4,135 | 69.40% |
| 2026 H1 | 586 | 855 | 2,761 | 3,616 | 68.56% |

The period table is candidate-slot based across nine audited identities,
including exact `cash`; the 2024 H1 and 2026 H1 XLSX filing counts differ from
the accepted all-format period counts because the two XBRL rows are excluded
from this XLSX-specific audit.

## Co-occurrence

Across 5,963 XLSX filings, all nine audited identities are never jointly
present. For the eight core identities excluding exact `cash`, complete
co-occurrence increases from **2,257** filings under the accepted parser to
**4,287** filings under the strict audit decoder. Pair counts are preserved in
external `cooccurrence.json` for review; no pair is treated as proof that a
missing third fact can be inferred.

## External audit artifacts

| Artifact | SHA-256 |
|---|---|
| `filing_template_audit.jsonl` | `71e51706cc16cc87cf12e3f9175d13f4ce33cb3b2a6d7ae8cf7f8a17a56e7f38` |
| `coverage_by_period.json` | `e78ee92794af9ce77a69df40f5a052b8ea5a5d309844f6f1837d3124796f61ab` |
| `cooccurrence.json` | `51b250ad35ac26f674c45e1ac3078f06f318bcf159b8da2b817ea02d750412eb` |
| `label_inventory.json` | `c0bf3bb0ea9f77d10ec022d4d3a93f5164e3937f64d11a55cf5cf86a64b01451` |
| `summary.json` | `f8a72f83704e5ba48d1e672a916708718909165746460a3b049558a807dac336` |
| `MANIFEST.json` | `follows the manifest file's self-listed artifact hashes` |

## Decision boundary

The missing-fact/template-drift hypothesis is **confirmed**. A future
separately authorized remediation may add strict exponent-form numeric support
to the canonical extractor, preserve visible-sheet and unit/conflict gates,
rerun the pinned census, and reconcile all hashes/counts. This audit itself
does not authorize that remediation, feature design, ratio construction, or
model work.

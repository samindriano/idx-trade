# Financial PIT Strict Scientific-Notation Remediation

Date: 2026-08-14 (Asia/Jakarta)
Branch: `data/financial-pit-scientific-notation-remediation-v1`
Status: `FINANCIAL_PIT_STRICT_SCIENTIFIC_NOTATION_REMEDIATION_CENSUS_RECONCILED_REVIEW`

## Scope and boundaries

This lane followed the accepted template-drift audit and changed only the
canonical numeric parsing path needed for strict ASCII scientific notation.
It reused the same immutable 6,108 scope-reclassification rows and 5,965
PIT-ready filing attachments. No provider/network call, redownload, new fact
label, ratio/feature derivation, model work, or protected-outcome access took
place.

The parser preserves exact labels, visible worksheets, current-period context,
presentation unit/currency/scale, label-priority/conflict rules, XBRL
taxonomy/context rules, and PIT publication/version/hash gates. Scientific
notation is accepted in native, inline-string, and shared-string XLSX cells
only when it satisfies the existing strict ASCII numeric grammar. Locale
guessing, fuzzy labels, hidden-sheet evidence, inferred values, and malformed
exponents remain rejected.

## Engineering remediation

- Added optional `[eE][+-]digits` to the existing ASCII decimal grammar.
- Routed visible XLSX inline/shared-string values through the same parser as
  native numeric cells.
- Added adversarial tests for positive/negative exponents, explicit signs,
  parenthesized negatives, malformed exponents, and nonnumeric text.
- Added an end-to-end inline scientific-value regression test.
- Added runtime code-commit provenance to the census manifest.

## Census result

Final external root:
`D:\Documents\Project\idx-financial-pit-scientific-notation-remediation-census-20260813-v3`

Inputs:

- scope rows SHA-256:
  `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9`;
- accepted census lineage: 6,108 exact joins, 5,965 PIT-ready filings;
- 5,963 XLSX and 2 XBRL filings processed;
- runtime code commit:
  `535946907bf12a69614e29e7b1cc1d5d756e51f5`.

| Core fact | Extracted | Coverage |
|---|---:|---:|
| revenue | 4,292 | 71.9531% |
| net income | 4,696 | 78.7259% |
| attributable net income | 4,698 | 78.7594% |
| total assets | 4,698 | 78.7594% |
| total liabilities | 4,697 | 78.7427% |
| total equity | 4,697 | 78.7427% |
| cash and cash equivalents | 4,306 | 72.1878% |
| exact `cash` | 392 | 6.5717% |
| operating cash flow | 4,691 | 78.6421% |

Overall statuses: `37,167 EXTRACTED`, `15 UNRESOLVED_PERIOD`, and `64
UNRESOLVED_UNIT`. Exclusions remain `143 SCOPE_UNRESOLVED`; no excluded row
was repaired or included.

The eight-fact complete co-occurrence count is **4,287 filings**, exactly
matching the accepted template-drift audit prediction. The corresponding
parser-era count was 2,257. The 4,287 count excludes exact `cash`, and no
missing fact is inferred from co-occurrence.

## Reconciliation against the accepted audit

The final census matches the audit-effective counts exactly for the main
recoverable facts, with one representation detail: the audit is XLSX-only,
while the census also retains the two accepted XBRL rows. The remaining
differences are therefore explained by the already accepted XBRL
period/taxonomy statuses, not by a label or exponent discrepancy.

The parser now recovers the formerly rejected H1-2025 onward scientific-value
cells without relaxing semantic gates. Remaining missing, unit, period,
taxonomy, conflict, unsupported, publication, linkage, and version gaps stay
fail-closed.

## External artifact hashes

| Artifact | SHA-256 |
|---|---|
| `fact_records.jsonl` | `3cba29b53a8f3d68bae016adf59ffe3edb385c690b44d843a1790227b4152575` |
| `filing_diagnostics.jsonl` | `a0a47d4fcfc58518ae97149722f4fb44c96b8c9430b51f1e9199bc09926fb5f4` |
| `coverage.json` | `fcccd4eef062723a088f534b9b1a2b8e2016d3de150b39634622c7a4bb5ace1f` |
| `exclusions.json` | `209e9f2b2c8543b46c66023e5d29162d5db84dbfa7d86ee798388d07a4c7ec4c` |
| `summary.json` | `dc6c4e8f45829162ab9984292c5a706893e07c8b5761e8454c7ba3555cd7e316` |
| `MANIFEST.json` | `95db03c431dadb5a0af749fd63687f39c8a68d450d7dee17c4c5c53c5bf73d7b` |

The manifest records runtime code commit
`535946907bf12a69614e29e7b1cc1d5d756e51f5` and the immutable input rows SHA.

## Validation and decision boundary

- focused Financial PIT tests: `29 passed`;
- full pytest: `531 passed, 0 failed, 3 existing FutureWarnings`;
- `git diff --check`: PASS for the task changes;
- network calls: `0`.

The scientific-notation remediation is reconciled and ready for independent
review. This result does not authorize ratios, fundamental features, model
work, or a feature contract freeze.

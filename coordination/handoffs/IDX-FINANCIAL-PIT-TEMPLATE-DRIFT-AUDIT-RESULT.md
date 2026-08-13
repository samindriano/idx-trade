# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-TEMPLATE-DRIFT-AUDIT
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `419f0be54a7b08ee958c52b8a727be9423286d96` accepted census lineage
branch: `data/financial-pit-template-drift-audit-v1`
head_commit: `5a1367b74f7d2d3ef188fed9f2b86b668f0ff247`

## Scope

Bounded offline missing-fact/template-drift and co-occurrence audit over the
5,963 accepted XLSX joins. The two accepted XBRL joins were not included in the
XLSX drift calculation and remain governed by their existing XBRL statuses.

No network calls, redownloads, financial facts beyond exact-label audit
evidence, ratios/features, models, or protected outcomes.

## Findings

- Candidate density drop is primarily numeric serialization drift.
- Exact canonical labels and current-period contexts remain present.
- Scientific notation is common after 2025 Q1: 3,420 value cells in 2025 H1,
  3,098 in 2025 9M, 3,608 in 2025 FY, 3,391 in 2026 Q1, and 3,048 in 2026 H1.
- Hidden/veryHidden duplication is a secondary drift; hidden sheets remain
  excluded and are not evidence.
- No fuzzy label mapping or guessed semantic mapping was used.

## Coverage result

For the 5,963 XLSX filings, strict exact-label/current-context/scientific-
notation audit-effective coverage is:

| Fact | Parser | Audit-effective | Recoverable drift |
|---|---:|---:|---:|
| revenue | 2,414 | 4,291 | 1,877 |
| net income | 2,965 | 4,696 | 1,731 |
| attributable net income | 2,977 | 4,696 | 1,719 |
| total assets | 2,473 | 4,696 | 2,223 |
| total liabilities | 2,621 | 4,696 | 2,075 |
| total equity | 2,645 | 4,696 | 2,051 |
| cash equivalents | 2,573 | 4,304 | 1,731 |
| exact cash | 341 | 392 | 51 |
| operating cash flow | 2,944 | 4,691 | 1,747 |

Eight non-exact-cash core facts co-occur in 2,257 parser filings and 4,287
audit-effective filings. No missing fact is inferred from pair/co-occurrence.

## External artifacts

Root:
`D:\Documents\Project\idx-financial-pit-template-drift-audit-20260813-v1-run3`

Manifest inputs:

- reclassification rows SHA-256:
  `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9`;
- accepted census manifest SHA-256:
  `e85469a52f749ab72869716b2689cfb2005e222103e2bfc7fdec1de4264eb872`.

Result artifact hashes are pinned in the checkpoint and external
`MANIFEST.json`.

## Decision and next boundary

`TEMPLATE_SERIALIZATION_DRIFT_CONFIRMED_EXACT_LABELS_RETAINED`.

This is an audit result only. Do not modify the canonical extractor, materialize
financial features, derive ratios, train models, access outcomes, or rerun the
census until ChatGPT authorizes the next bounded remediation/spec.

## Validation

- focused template-drift + accepted census/fact tests: `17 passed`;
- full pytest: `519 passed, 0 failed, 3 warnings`;
- no provider/network access.

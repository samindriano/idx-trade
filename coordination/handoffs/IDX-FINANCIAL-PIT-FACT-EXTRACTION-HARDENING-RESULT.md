# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-FACT-EXTRACTION-HARDENING
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `4013f90a56edc6d8409e6a7514a9170d5f301aff`
branch: `data/financial-pit-fact-extraction-hardening-v1`
result_commit: `c609e688c424f0d16be69edca6772f0b050e8077`

## Scope

Hardening only for explicit XLSX currency/unit/scale semantics, repeated-label
statement-role/location/context selection, and XBRL taxonomy/schemaRef/unit/
context semantics. Reused the immutable 36-filing sample and attachments.
No network calls, redownload, market-wide extraction, ratios/features, model
work, or protected-outcome access.

## Files changed

- `src/idx_trade/financial_fact_table.py`
- `tests/test_financial_fact_table.py`
- `docs/checkpoints/2026-08-13_FINANCIAL_PIT_FACT_EXTRACTION_HARDENING.md`
- this handoff

## Findings

- candidate observations: 212 before and after;
- `EXTRACTED`: 141 -> 197;
- former `UNRESOLVED_UNIT`: 42 -> 0;
- former `CONFLICTING_FACTS`: 14 -> 0;
- `UNRESOLVED_PERIOD`: 15 -> 15;
- former unit/conflict cases safely extractable: 56 / 56;
- actual XBRL taxonomy version in both sample filings: `2020-01-01`;
- adversarial focused tests added: 6.

The 14 repeated-label cases are resolved only because the final OCF label has
explicit higher semantic authority than the intermediate subtotal. Same-level
conflicts still fail closed. XLSX body/narrative currency occurrences are no
longer presentation evidence. XBRL plain text, invalid contexts, invalid
units/scales, and missing/conflicting official taxonomy identity fail closed.

## External artifact hashes

Root:
`D:\Documents\Project\idx-financial-pit-fact-extraction-hardening-20260813-v1-run1`

- `sample_selection.json`: `de7381c595b09044c1760e5e4298ea883427576125a6f9cfdd5a06648d559abe`
- `fact_records.jsonl`: `d56415c65148141d4e571ab7d0c9b25e436a0548ce22de90242dc47f29c2d512`
- `filing_diagnostics.jsonl`: `c29792a51deeef71c939b14328dccdd7fd8b660009764f07e11a57e74f0537c6`
- `summary.json`: `2f72cebdcfe902bf1b14b5ee5f8c259b92d893f83a75ed1df5d76fdd243d80a9`
- `MANIFEST.json`: `9cb0f5797145921a8871b21542afa7604343efec5450ef8dea41967764ecdabb`

## Decisions and blockers

- bounded sample hardening: complete;
- market-wide fact extraction: remains blocked/not authorized;
- no ratios, features, models, or outcomes were touched;
- no remaining old unit/conflict case was promoted without explicit evidence.

## Validation

- focused `tests/test_financial_fact_table.py`: 13 passed;
- full repository pytest: 514 passed, 0 failed, 3 warnings;
- `git diff --check`: passed.

## Recommended next action

Independent ChatGPT review of the code, sample metrics, and fail-closed
taxonomy/unit/context contract. Do not begin market-wide extraction until the
review separately authorizes it.

# Handoff

from: Codex MAIN
to: ChatGPT reviewer / Financial PIT owner
task_id: IDX-FINANCIAL-PIT-FACT-SCHEMA-FEASIBILITY
model_used: Luna xhigh root + one read-only Luna xhigh worker
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 45d36eda095ea975182565804baaf899a9706c58
branch: data/financial-pit-fact-schema-v1
head_commit: pending

## Scope

Bounded offline version-aware Financial PIT fact-schema and extraction
feasibility audit over 36 accepted filings. No provider/network call,
redownload, market-wide extraction, features, modeling or protected outcomes.

## Files changed

- `src/idx_trade/financial_fact_table.py`
- `tests/test_financial_fact_table.py`
- `docs/checkpoints/2026-08-13_FINANCIAL_PIT_FACT_SCHEMA_FEASIBILITY.md`
- this handoff

## Findings

- Schema prototype preserves filing/fact identity, publication/knowledge time,
  attachment/source provenance, scope, unit/scale, fiscal context, source
  locator, taxonomy metadata and immutable version identity.
- Sample: 36 filings, 34 XLSX + 2 XBRL, 19 consolidated + 17 separate, 18
  financial/sharia + 16 general XLSX, years 2024-2026, FY/Q1/H1/9M.
- 212 candidate observations: 141 extracted (66.5094%), 42 unresolved unit, 14
  conflicting facts, 15 rejected prior-context XBRL candidates.
- Explicit XLSX/XBRL evidence is usable for further bounded work; unit/scale,
  repeated-label, taxonomy-version and revision-history gaps remain.
- Three correction markers were observed in accepted evidence (RONY, BAPA,
  MUTU), but the accepted census does not retain a complete prior-version chain.

## Decision

`BOUNDED_SCHEMA_FEASIBILITY_GO_MARKET_WIDE_EXTRACTION_BLOCKED`.
The immutable market-wide fact table is not yet defensible. Do not derive
financial ratios/features or begin market-wide extraction without a separate
authorization and coverage gate.

## Validation

- focused Financial PIT + fact-table tests: passed;
- full pytest: 509 passed, 0 failed, 3 existing FutureWarnings.

## External artifact manifest

External root:
`D:\Documents\Project\idx-trade-financial-pit-fact-schema-20260813-v1`

- `fact_records.jsonl`: `6e4eb9cabffd5352e98fc966201b4ec4860991565a363baba54999d8cf593d54`
- `filing_diagnostics.jsonl`: `41d25abd0aeccbbb4a5d8bd28db3ef670b9cce0968e431341c2e572c9d2fc130`
- `sample_selection.json`: `de7381c595b09044c1760e5e4298ea883427576125a6f9cfdd5a06648d559abe`
- `summary.json`: `e3e9c3aeb40e0bffefaa800872e4aaaca5ec645d43f9c4f09d5ad44c7ee0e8ec`
- `MANIFEST.json`: `6fb43ae8a4df62aab5a63faa4729e193f58c5efcc54cbea4ef3dc4e82e539b5f`

## Recommended next action

ChatGPT review should decide whether to authorize a second bounded resolver
hardening step for unit/scale and XBRL taxonomy/version semantics, or keep
Financial PIT fact extraction blocked. No model or outcome work is implied.

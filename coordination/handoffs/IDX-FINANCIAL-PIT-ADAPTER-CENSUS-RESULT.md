# Handoff

from: Codex
to: ChatGPT independent review
task_id: IDX-FINANCIAL-PIT-ADAPTER-CENSUS
model_used: GPT-5 Codex / Luna xhigh orchestration policy
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: accepted `data/financial-pit-v1@25eaa67a7f5446234db470756fe8b5c12cbb7696`
branch: `data/financial-pit-adapter-census-v1`
scope: bounded direct-IDX Financial PIT adapter and 2024-2026 source-readiness census
head_commit: pending commit

## Files changed

- `src/idx_trade/financial_pit_adapter.py`
- `scripts/financial_pit_coverage_census.py`
- `tests/test_financial_pit_adapter.py`
- `docs/checkpoints/2026-08-13_FINANCIAL_PIT_ADAPTER_CENSUS_RESULT.md`
- this handoff

## Findings

- eligible universe: 737 tickers, SHA-256
  `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe`;
- expected issuer-periods: 7,370 (2024 Q1/H1/9M/FY, 2025 Q1/H1/9M/FY,
  2026 Q1/H1);
- reports found: 6,580;
- relevant filename announcement matches: 6,212;
- exact dual-source attachment hash joins: 6,108;
- PIT-ready: 0 because statement scope is not endpoint-declared and was not
  guessed;
- scope-unresolved: 6,108;
- missing publication linkage: 1,158;
- ambiguous attachments: 74;
- attachment hash conflicts: 2;
- HTTP/provider failures: 28;
- report-not-found: 790;
- final verdict: `PARTIAL_SOURCE_USEFUL_PIT_COVERAGE_INCOMPLETE`.

## Provenance

External raw root:
`D:\Documents\Project\idx-trade-financial-pit-adapter-census-20260813-v1`

Final manifest:
`MANIFEST__rerun_v6.json`  
Manifest SHA-256:
`e675a258e5281eb01032d6d4b73c7a94f41871b06550e2253df3b7ac7cd9946e`

Raw captures and attachments remain outside Git. The adapter preserves changed
raw response versions by content hash and rejects logical filing hash conflicts.

## Decisions made

- naive IDX publication timestamps are interpreted as Asia/Jakarta then stored
  as UTC ISO values;
- `CreatedDate` is not publication time;
- incomplete `ResultCount`/rows responses fail closed;
- exact filename matching is not enough for an exact join; both attachment
  byte hashes must agree;
- unresolved statement scope is not PIT-ready;
- no facts, ratios, features, model artifacts, outcomes, or other data lanes
  were touched.

## Validation

- focused Financial PIT + adapter tests: 17 passed;
- full pytest: 497 passed, 0 failed, 3 warnings;
- raw capture manifest and coverage artifacts are external and hash-pinned.

## Blocking risks

- scope extraction requires a version-aware XLSX/PDF/XBRL parser;
- 74 ambiguous matches, 2 byte conflicts, 28 HTTP failures and 1,158
  publication-linkage gaps remain;
- complete revision/restatement discoverability is not proven;
- no market-wide PIT-ready financial table may be claimed.

## Recommended next action

ChatGPT review the adapter contract and census report. If accepted, authorize a
separate parser/scope-resolution milestone; do not use this census as financial
features or model input.

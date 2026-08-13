# Handoff: Financial PIT Direct IDX Publication-Chain Audit

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-DIRECT-IDX-PUBLICATION-CHAIN-AUDIT
model_used: Codex
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `b446c3cd6fbf057933202ae207d978b42edc5694`
branch: `data/financial-pit-v1`
scope: bounded direct IDX Financial PIT publication-chain audit only

## Files changed

- `docs/checkpoints/2026-08-13_FINANCIAL_PIT_DIRECT_IDX_PUBLICATION_CHAIN_AUDIT.md`
- `coordination/handoffs/IDX-FINANCIAL-PIT-DIRECT-IDX-PUBLICATION-CHAIN-AUDIT.md`

Raw responses and official attachments remain outside Git at:
`D:\Documents\Project\idx-trade-financial-pit-direct-audit-20260813-v6`.

External manifest SHA-256:
`a60f7af03e42b4c02c8dcafa5eec7064b3bb16ff3fe3b826cf9976f6b699a898`.

## Findings

- Direct `ListedCompany/GetFinancialReport` and direct
  `ListedCompany/GetAnnouncement` both returned HTTP 200 through
  `nichsedge/idx-bei` / `curl_cffi` Chrome impersonation for the bounded primary
  samples.
- BBCA FY2024, BBCA Q1 2025, AADI FY2024, and TLKM 9M 2025 joined
  deterministically by exact attachment filename: 4/4.
- Report-file and announcement attachment bytes matched in every primary
  variant. Existing preserved XLSX hashes also matched 4/4. PDF, XLSX, and
  XBRL ZIP were directly retrievable and non-empty.
- `File_Modified` equals `TglPengumuman` to second precision in primary samples.
  IDX exposes no timezone; retain explicit `Asia/Jakarta` interpretation before
  UTC conversion. `CreatedDate` can be later and is not publication time.
- BBCA FY2022 and Q1 2023 reports were still discoverable from
  `GetFinancialReport`, but their Jan/Apr 2023 `GetAnnouncement` queries returned
  `ResultCount=0`. BBCA FY2023 Jan 2024 remained joinable.
- A BBCA 2024-01-01 through 2026-08-13 query returned `ResultCount=197`; the
  100-row page-2 probe returned zero while `pageSize=1000` returned all 197.
  Pagination must therefore be validated, not inferred.
- The bounded BBCA history contained one observed financial announcement per
  period and no duplicate restatement/version chain. `GetFinancialReport` returns
  one current row and exposes no immutable revision list. Revision completeness
  remains unresolved.

## Decision

`PARTIAL_SOURCE_USEFUL_PIT_COVERAGE_INCOMPLETE`

The direct source is useful for bounded source discovery and PIT publication
linkage while the issuer history remains visible. It is not complete PIT-ready
market acquisition. Do not bulk backfill, derive financial features, model,
access outcomes, or overwrite prior filing versions.

## Validation

To be run on the final documentation commit:

- `python -m pytest tests/test_financial_pit.py -q`
- `python -m pytest -q`
- `git diff --check`

## Requested review decision

ChatGPT should decide whether to authorize a separate bounded adapter
implementation. Any adapter must fail closed on incomplete pagination or missing
announcement linkage, preserve all raw/file hashes and revisions, attach the
explicit IDX-local timezone, and require statement scope from parsed filing
content rather than endpoint metadata.

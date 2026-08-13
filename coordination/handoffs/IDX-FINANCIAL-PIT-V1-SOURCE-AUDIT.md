# Handoff: Financial PIT V1 Source Audit

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-V1-SOURCE-AUDIT
model_used: Codex
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `b442a29cb24bdb4f29c4907b64ba26c8158951db`
branch: `data/financial-pit-v1`
scope: bounded Zapi/official IDX Financial Statements PIT source audit only

## Files changed

- `docs/checkpoints/2026-08-12_FINANCIAL_PIT_V1_SOURCE_AUDIT.md`
- `coordination/handoffs/IDX-FINANCIAL-PIT-V1-SOURCE-AUDIT.md`

No source or test implementation was changed because the Financial PIT scaffold and focused tests were already passing.

## Findings

- Zapi wrapper: `/v1/finance:idx/financial-report`.
- Zapi raw passthrough: `/v1/finance:idx/raw` with upstream `ListedCompany/GetFinancialReport`.
- Official issuer publication metadata: `ListedCompany/GetAnnouncement`.
- Representative wrapper/raw parity: 4/4 records and 4/4 attachment lists.
- Representative financial-report/issuer-announcement official XLSX byte equality: 4/4.
- `File_Modified` agrees with issuer `TglPengumuman` for the four cross-checks; use the issuer announcement timestamp as the PIT publication candidate, not `created_at` or workbook board date.
- Source timestamps are naive IDX-local values with no timezone field. Canonical ingestion must explicitly attach `Asia/Jakarta` and convert to UTC before applying the Financial PIT contract.
- Sampled Q1/H1/9M statements are cumulative YTD durations; FY is annual. Scope is explicit and must remain consolidated/separate.
- Raw official captures and attachments are outside Git at `D:\Documents\Project\idx-trade-financial-pit-20260812`.
- The public issuer announcement response currently advertises a three-year range beginning 2023-08-12. This prevents a complete 2021–2026 publication-time claim.
- No immutable financial-statement revision chain was demonstrated in the representative issuer histories.

## Evidence hashes

Raw passthrough captures:

- `zapi_raw_financial_report_BBCA_2024_audit.json`: `ea76c2a9cbb7ec672c495974f318fa52af37d23395cac016bf6247562e792c97`
- `zapi_raw_financial_report_BBCA_2025_tw1.json`: `e341a69cdeb47e089b73419e22428f823f90cd31dc579682ef88e3d52ac80fa9`
- `zapi_raw_financial_report_AADI_2024_audit.json`: `b3e85fca735220a3e64c5c6aeaee27e648b8ceccd75f7e381404e518bd40f47c`
- `zapi_raw_financial_report_TLKM_2025_tw3.json`: `493ee0dbeef7ed9580c1dd060c675d55ee84a2651f4fa130e7bd7def6c04cac3`

Financial-report wrapper captures:

- BBCA 2024 audit: `b2a934b94b4c8842e415ede9de638ce20d748b62a9e0a94d1fb5bc46074d2f39`
- BBCA 2025 Q1: `8bedc5b4d157d134b558b1d0e0206d24b0f8f579da8e71135763b2b9c5ecfbd9`
- AADI 2024 audit: `2c76cd67f21f62aa2cce84ebd716c4f7675a4bd61d97ee929a84ec353c7e679e`
- TLKM 2025 9M: `d0c065e3b558273734a0927a1177b3caf7016834f570815b4af9088593815da9`

Issuer announcement captures:

- BBCA: `0bcaeb138c963eef622c300f1be3668ce32c9968d2e8b93de67613b74763a5e7`
- AADI: `71e51d616f2ffc69c3b08b65505aa1e7b0134064783f69828aaf66a8d81a94e1`
- TLKM: `eab68204eb8bc846b291dea08422e1c14e5e335216cdf1e6498bb32d57ca577d`

## Tests

- `python -m pytest tests/test_financial_pit.py -q`: **8 passed**.
- `python -m pytest -q -rA`: **479 passed, 0 failed, 3 warnings, 29.02s**.
- In-memory contract smoke: four canonical filings and four filing-bound facts; as-of visibility passed before/at each publication timestamp.

## Decision

`CONDITIONAL_PASS_SOURCE_DISCOVERY_ONLY_NO_GO_FOR_COMPLETE_FINANCIAL_PIT_ACQUISITION`.

Do not bulk backfill, derive financial features, train models, access outcomes, or change other data lanes from this handoff. The next authorized work should be a paginated, provenance-preserving adapter plus a publication-time/revision completeness gate.

## Recommended next action

ChatGPT review should decide whether to authorize implementation of the bounded adapter and its source-timezone/announcement-join contract. Historical reports older than the public issuer-announcement retention window should remain unknown unless an official archive path is independently established.

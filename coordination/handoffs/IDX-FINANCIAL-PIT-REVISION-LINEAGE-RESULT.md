# Handoff

from: Codex MAIN  
to: ChatGPT reviewer / Financial PIT owner  
task_id: IDX-FINANCIAL-PIT-REVISION-LINEAGE  
model_used: Luna xhigh root  
reasoning_level: xhigh  
source_repository: samindriano/idx-trade  
source_commit: 4013f90a56edc6d8409e6a7514a9170d5f301aff  
branch: data/financial-pit-revision-lineage-v1  
head_commit: 77737403d3bed19e509d417d97c841d35afa06c8  

## Scope

Bounded direct-IDX correction/restatement lineage audit for RONY FY2024,
BAPA FY2025 and MUTU H1 2025. No market-wide extraction, unit/scale repair,
features, modeling or protected outcomes.

## Files changed

- `docs/checkpoints/2026-08-13_FINANCIAL_PIT_REVISION_LINEAGE_AUDIT.md`
- this handoff

Raw captures and attachment bytes are external only:
`D:\Documents\Project\idx-trade-financial-pit-revision-lineage-20260813-v1`.

## Findings

- Six metadata requests plus three current-report attachment requests, all
  HTTP 200.
- Each target exposes two observable versions with distinct Asia/Jakarta
  `TglPengumuman` values and distinct bytes for XLSX, inlineXBRL and instance.
- Current `GetFinancialReport` points to the latest correction/revision for all
  three cases.
- The original target XLSX URL still returned original bytes for all three.
- Current `File_Modified` agrees with latest `TglPengumuman` to the second, but
  is not safe to use as the original version's publication timestamp.
- BAPA original reference is the literal response value `tes`; retained as a
  metadata anomaly, not guessed or normalized.

## Classification

| Case | Classification |
|---|---|
| RONY FY2024 | `VERSION_CHAIN_PIT_SAFE` |
| BAPA FY2025 | `VERSION_CHAIN_PIT_SAFE` with literal `tes` reference anomaly |
| MUTU H1 2025 | `VERSION_CHAIN_PIT_SAFE` |

## Policy decision

`DEFENSIBLE_BOUNDED_POLICY`:

> Use an observed filing version only from its own proven publication timestamp
> onward; if an earlier version is unavailable, treat the issuer fact as
> missing before the observed version rather than backfilling.

The policy is not a market-wide completeness claim. Outside the three cases,
the adapter must fail closed as `OBSERVED_LATEST_VERSION_ONLY_FAIL_CLOSED`,
`RETROSPECTIVE_BYTE_REPLACEMENT_RISK` or `UNRESOLVED` when the relevant
evidence is absent or contradictory.

## External evidence and hashes

External root:
`D:\Documents\Project\idx-trade-financial-pit-revision-lineage-20260813-v1`

- `revision_lineage_audit.json`: `c016b32168383db6c3b82a9b8b0f62ed2cd849a3aae98307238f47a8d2e4f623`
- `MANIFEST.json`: `70f8ee6f6efc1a2b4de73745021f8eff655e70461fe3032f98287a3ee037de82`
- `request_manifest.json`: `f3a419f8edcc11f49bc44d17232349103565567f5b6ef6b8bc2dded287d6d900`
- `lineage_candidates.json`: `2fb00496d8d38e94ab3ed6bb5b37666b7791e010fdae844e3ba41457ba0f796e`

The audit JSON records exact announcement URLs, report paths, filenames,
timestamps, SHA-256 values and current-pointer comparisons for every case.

## Validation

- Focused Financial PIT tests: `17 passed`.
- Full pytest: `509 passed, 0 failed, 3 existing FutureWarnings`.
- Collection check: `509 tests collected`.
- `git diff --check`: passed.

## Recommended next action

Stop for ChatGPT review. Do not start market-wide correction/restatement
reconstruction, unit/scale repair or feature extraction until a separate
coverage authorization is given.

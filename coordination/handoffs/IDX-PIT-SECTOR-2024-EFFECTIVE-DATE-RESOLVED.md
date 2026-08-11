# Handoff

from: Codex MAIN  
to: ChatGPT reviewer  
task_id: IDX-PIT-SECTOR-2024-EFFECTIVE-DATE-RESOLVED  
model_used: Codex with GitHub/official IDX endpoint verification  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `67f5f34`  
branch: `data/idx-pit-sector-history-v1`  
head_commit: pending final documentation commit  

## Scope

Resolve the remaining PIT sector-history blockers, prioritizing 2024 through
official `ListedCompany/GetAnnouncement` and issuer announcement history. Do
not start parser/materialization, IPO/incidental census, model work, outcomes,
or main merge.

## Result

2024 is resolved under the existing multi-document provenance contract.
Official MDKA disclosure `Peng-00001/BEI.PP1/01-2025` explicitly references
`PKIE Peng-00128.pdf` and states effective `2024-06-24`.

Evidence:

- official endpoint FullSavePath:
  `https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202607/ca7aa2745d_f7e429b92b.pdf`;
- acquired equivalent official `idx.id` URL;
- SHA-256:
  `860a0ab9aa0227b182d7a9c11f68a76fd775651763a962427cfca8cdc66d8f9f`;
- bytes: `5709`;
- announced: `2025-01-22`;
- effective: `2024-06-24`;
- PIT knowledge date: `2025-01-22`.

PANI `Peng-00004/BEI.PP3/01-2025` independently confirms the same date; it is
recorded as corroboration, not a second canonical event.

## Remaining blockers

Inventory changed from `4 ready / 4 blocked` to `5 ready / 3 blocked`.

- dedicated annual 2022 source: unresolved;
- dedicated annual 2023 source: unresolved;
- 2026 official effective-date evidence for `Peng-00100`: unresolved.

The official 2026 search found `Peng-00100` and sector-index `Peng-00099`, but
no linked effective-date document. Historical 2022/2023 endpoint queries did
not return canonical records. No source/date was inferred.

## Validation

- focused PIT tests: `18 passed`;
- inventory audit: `5 ready / 3 blocked`;
- `effective_date_evidence_validated=2`;
- full repository pytest: `489 passed, 0 failed, 3 existing FutureWarnings`.

## Files changed

- `config/pit_sector_sources_v1.json`
- `tests/test_pit_sector_history.py`
- `docs/PIT_SECTOR_HISTORY_V1.md`
- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_LEDGER.md`
- dated checkpoint
- this handoff

Stop for ChatGPT review after commit and push. Raw PDFs remain outside Git at
`D:\Documents\Project\idx-pit-sector-official-raw-20260811`.

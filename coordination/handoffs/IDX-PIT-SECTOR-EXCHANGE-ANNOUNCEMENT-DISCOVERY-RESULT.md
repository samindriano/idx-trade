# Handoff

from: Codex  
to: ChatGPT review  
task_id: IDX-PIT-SECTOR-EXCHANGE-ANNOUNCEMENT-DISCOVERY  
model_used: Codex  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `b3ac8d0dc39d56be0f80c4a6af57fe7ba60b68d9`  
branch: `data/idx-pit-sector-history-v1`  

## Scope

Investigated the official IDX frontend/API retrieval path for exchange-level
announcements, then queried the 2022, 2023, and 2026 IDX-IC classification
windows. No parser, materialization, census expansion, model, outcome, Path
Risk, fresh-forward, or `main` work was authorized or performed.

## Findings

- Official exchange listing path: `/primary/NewsAnnouncement/GetAllAnnouncement`.
- Request parameters: `keywords`, `pageNumber`, `pageSize`, `dateFrom`,
  `dateTo`, `lang`.
- Attachment contract: `Attachments[].FullSavePath`; `IsAttachment=0` is the
  primary document in the frontend.
- Public listing disclaimer: only the latest three years are shown; older
  history is directed to TICMI.
- 2022 targeted June/July query: `ItemCount=0`; no canonical ref/date promoted.
- 2023 targeted June/July query: `ItemCount=0`; no canonical ref/date promoted.
- 2026 canonical: `Peng-00100/BEI.POP/06-2026`, published 2026-06-24 18:55.
  PDF: 312,989 bytes, SHA-256
  `8b5413f18afc75cc17260c2400611d710e8f270d46a49c5a396f557b27cf8b25`.
  The PDF has issuer classification changes but no explicit effective date.
- `Peng-00099/BEI.POP/06-2026` is sector-index evaluation/reconciliation
  evidence. Its 2026-07-01 index period was not promoted or used to infer
  issuer classification timing.

## Decisions

No blocker was genuinely resolved in this pass. Inventory remains `5 ready / 3
blocked`: annual 2022, annual 2023, and canonical 2026 effective-date
evidence. No announcement ref or effective date was guessed.

## Files changed

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_LEDGER.md`
- `docs/PIT_SECTOR_HISTORY_V1.md`
- `docs/checkpoints/2026-08-11_PIT_SECTOR_EXCHANGE_ANNOUNCEMENT_DISCOVERY_RESULT.md`
- `coordination/handoffs/IDX-PIT-SECTOR-EXCHANGE-ANNOUNCEMENT-DISCOVERY-RESULT.md`

External raw/frontend audit directory (not committed):
`D:\Documents\Project\idx-pit-sector-official-raw-20260811`.

## Validation

- Focused PIT suite: 18 passed.
- Full suite: 489 passed, 0 failed, 3 existing FutureWarnings.

## Recommended next action

Keep the three blockers fail-closed. A future source-discovery pass must use a
new official archival path or immutable official attachment for 2022/2023, and
an explicit official effective-date document linked to `Peng-00100` for 2026.

# Handoff

from: Codex MAIN  
to: ChatGPT reviewer  
task_id: IDX-PIT-SECTOR-OFFICIAL-RAW-ACQUISITION  
model_used: Luna xhigh workers with MAIN integration  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `59cfb2129350146e322c7a9e31ae3e52bee44899`  
branch: `data/idx-pit-sector-history-v1`  
head_commit: pending documentation commit  

## Scope

Resolve official IDX raw attachments, acquire them outside Git, hash and
inspect layouts, update factual source metadata/docs, and stop. No model,
sector score, Path Risk run, fresh-forward outcome, V3-B change, or main merge
was authorized or performed.

## Files changed

- `config/pit_sector_sources_v1.json`
- `docs/PIT_SECTOR_HISTORY_V1.md`
- `docs/checkpoints/2026-08-11_PIT_SECTOR_OFFICIAL_RAW_ACQUISITION_RESULT.md`
- this result handoff
- `docs/CURRENT_STATUS.md` and `docs/PROJECT_LEDGER.md` are updated only for
  status continuity in the same commit.

Raw files are not committed. They are outside Git at
`D:\Documents\Project\idx-pit-sector-official-raw-20260811`.

## Findings

Verified official raw attachments:

- baseline `Peng-00007/01-2021`: SHA
  `0b6b2e136e0e729fc80fb5bd97e73623aab7c461af89552d6e030837635bbcdd`;
- annual 2021 `Peng-00171`: SHA
  `2eb49058d63dcf16e8bb81dd3788364374adefdf1b92baa4b5fd406bcec51fbf`;
- sector-index reconciliation `Peng-00150/06-2022`: SHA
  `1f13b7b3cdc75ed22b9848c08666a18488690009a98aaaa6586f745a6e9c18be`;
- sector-index reconciliation `Peng-00156/06-2023`: SHA
  `da4589ee59889e606e5f8cd26cce19b119107e1a89bd9aa13b763b9071a06aca`;
- canonical PALM `Peng-00236/09-2023`: SHA
  `3b85b0f1bbd0cdee1ef6dc99de2b5570da892e908458303d0fbfe29bf81959d9`;
- annual 2024 `Peng-00128`: SHA
  `4ecf5ebb2809c9007b68bfe0aa1c426428d77178ff9acbf744364afba00ad223`;
- annual 2025 `Peng-00110`: SHA
  `09ecc0b059b6c486aa3220faacb55fa638e1991d26c37e26d9455fec0ceec7de`;
- annual 2026 `Peng-00100`: SHA
  `d95b27f4bab74a2da9ab737c3bdd96bc4626cfb97635ffa32a9449be78d7db98`.

The canonical annual 2022 and 2023 classification references remain
unresolved. `Peng-00150` and `Peng-00156` were inspected and are sector-index
evaluation packages, so they are not promoted to canonical issuer
classification history. The canonical PALM, 2024, and 2026 raw documents do
not contain an effective date; no date was inferred. An official IDX issuer
disclosure supports PALM effective 2 October 2023 but remains supporting, not
the canonical source row.

## Decisions made

- Keep inventory fail-closed: `3` canonical sources ready, `5` blocked.
- Record recovered official URLs, raw SHA-256, size, content type/layout, and
  supporting evidence in `config/pit_sector_sources_v1.json`.
- Retain 2022/2023 sector-index packages only under reconciliation sources.
- Do not run bulk acquisition while any canonical source is
  `DISCOVERY_REQUIRED`.

## Validation

- Inventory CLI audit: `sources_total=8`, `sources_ready=3`,
  `sources_blocked=5`, `complete_for_acquisition=false`.
- Focused test: `tests/test_pit_sector_history.py` — `8 passed`.
- Working tree was clean before documentation edits; explicit `git -C` was
  used because the surrounding `Documents` folder is itself a separate Git
  repository.

## Blocking risks

- Dedicated annual classification raw announcements for 2022 and 2023 are
  still not identified.
- Canonical effective-date evidence is missing for PALM, 2024, and 2026.
- IPO initial classifications and other incidental classification changes
  still require a separate census after the canonical annual sources are
  complete.

## Recommended next action

Have ChatGPT review the factual source inventory and the distinction between
canonical classification events and sector-index reconciliation packages.
After approval, continue official-source discovery only for the listed
blockers; do not start `validate-history`, V3-D, or any model work yet.

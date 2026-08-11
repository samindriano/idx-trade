# Handoff

from: ChatGPT / MAIN
to: Codex local runtime + official-portal resolver
task_id: IDX-PIT-SECTOR-OFFICIAL-RAW-ACQUISITION
source_repository: samindriano/idx-trade
branch: data/idx-pit-sector-history-v1
scope: resolve official IDX raw attachments, acquire them outside Git, hash and inspect layouts; no model work

## Read first

1. `AGENTS.md`
2. `docs/checkpoints/2026-08-11_PIT_SECTOR_OFFICIAL_SOURCE_DISCOVERY_RESULT.md`
3. `docs/PIT_SECTOR_HISTORY_V1.md`
4. `config/pit_sector_sources_v1.json`
5. `src/idx_trade/pit_sector_history.py`
6. this handoff

## Goal

Turn the bounded source-discovery map into a factual raw-source manifest using official IDX portal/attachment evidence where available.

Priority unresolved canonical sources:

- 2021 annual classification change `Peng-00171/BEI.POP/06-2021`;
- 2022 dedicated annual classification-change announcement/ref + raw attachment;
- 2023 dedicated annual classification-change announcement/ref + raw attachment;
- PALM incidental 2023 `Peng-00236/BEI.POP/09-2023`;
- 2024 annual classification change `Peng-00128/BEI.POP/06-2024`;
- 2025 annual classification change `Peng-00110/BEI.POP/06-2025`;
- 2026 annual classification change `Peng-00100/BEI.POP/06-2026`.

The January 2021 baseline official package URL is already known and may be acquired as part of the manifest.

## Execution

Use Orchestra where useful because source-year resolution is parallelizable. Keep workers bounded to independent source/year searches or independent evidence review. MAIN integrates the factual manifest.

For every recovered source:

- verify it is an official IDX/BEI portal or official IDX-hosted attachment;
- record requested URL, final URL after redirects, announcement ref, announced date, effective date only when explicitly evidenced;
- download raw file outside Git;
- compute SHA-256;
- record content type, file type, byte size, and basic internal layout (ZIP members / XLSX sheet names / PDF page count if cheaply available);
- preserve ambiguity rather than infer missing dates or refs.

If an official attachment cannot be recovered, record the exact blocker and strongest evidence found. Do not substitute a sector-index evaluation announcement for a listed-company classification-change announcement.

## Output / documentation

Use a local evidence directory outside Git. Do not commit raw files.

In Git, update only factual metadata/docs needed to preserve results, especially:

- `config/pit_sector_sources_v1.json`;
- a new runtime/result checkpoint under `docs/checkpoints/`;
- this handoff/result handoff if useful.

Return a concise table containing per source:

`year/event | announcement_ref | official_raw_url | announced_at | effective_from | SHA-256 | raw type/layout | status/blocker`

Also report whether the current inventory is ready for parser implementation and which source classes remain unresolved.

## Hard boundaries

Do not:

- run V3-D or any sector-relative model;
- alter/fine-tune V3-B or V2;
- access fresh-forward realized outcomes;
- touch Path Risk sealed evidence;
- invent announcement refs, dates, or URLs;
- treat present-day sector labels as historical truth;
- commit downloaded raw artifacts;
- merge to main.

Stop after the acquisition/resolution report and Git documentation are pushed. Return the result to ChatGPT for parser/design review.

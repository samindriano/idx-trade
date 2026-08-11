# Checkpoint — PIT historical sector foundation implementation started

Date: 2026-08-11 (Asia/Jakarta)
Status: `PIT_SECTOR_DATA_FOUNDATION_IMPLEMENTATION_STARTED_SOURCE_INVENTORY_INCOMPLETE`
Branch: `data/idx-pit-sector-history-v1`
Base: `research/idx-ranking-v2-spec-v1` at source-research checkpoint HEAD `8a45f53d15bf0c0148fdcd11e848cf51c6e0d3bf`

## Decision

The recorded PIT historical sector direction is now authorized only as a **data-foundation/source-acquisition implementation track**.

This does not authorize a sector-relative model experiment.

## Implemented

- dedicated branch isolated from the frozen ranker;
- `config/pit_sector_sources_v1.json` source inventory with unresolved years kept explicit rather than guessed;
- `src/idx_trade/pit_sector_history.py`:
  - official-IDX HTTPS allowlist;
  - fail-closed redirect/network acquisition contract;
  - raw source SHA-256 manifesting;
  - inventory completeness gate;
  - canonical sector-event validation;
  - `pit_from = max(effective_from, announced_at)` semantics;
  - effective/PIT interval materialization;
  - point-in-time as-of join for future signal tables;
- `tests/test_pit_sector_history.py` adversarial/synthetic coverage;
- `docs/PIT_SECTOR_HISTORY_V1.md` data contract.

## Current source inventory

Ready reference:

- initial IDX-IC baseline announcement `Peng-00007/BEI.POP/01-2021`, announced 2021-01-13, effective 2021-01-25, historical package reference `https://www.idx.co.id/media/9594/idx-industrial-classification.zip`.

Known announcement references but attachment URLs still unresolved:

- 2024 `Peng-00127/BEI.POP/06-2024`, announced 2024-06-24, effective 2024-07-01;
- 2025 `Peng-00111/BEI.POP/06-2025`, announced 2025-06-23, effective 2025-07-01.

Still unresolved and intentionally not guessed:

- annual 2021;
- annual 2022;
- annual 2023;
- annual 2026;
- official attachment URLs for 2024/2025;
- IPO classifications between annual snapshots;
- any exceptional out-of-cycle reclassification events.

## Fail-closed behavior

Bulk acquisition is blocked while any required inventory row remains `DISCOVERY_REQUIRED`.

The code therefore cannot silently download only the easy years and produce an apparently complete history.

Source-specific parsers are also not frozen yet because the exact raw attachment formats have not all been acquired and inspected.

## Next work

1. finish official annual source discovery/inventory;
2. verify exact URLs, announcement dates and effective dates;
3. then run one raw source acquisition pass outside Git and SHA-pin every source;
4. inspect raw formats;
5. only then implement source-specific parsers and coverage reconstruction.

## Hard boundary

Do not:

- modify/reopen frozen V3-B;
- run V3-D or another sector-relative candidate;
- access fresh-forward outcomes;
- backfill present-day sectors historically;
- use third-party sector data as silent canonical truth;
- touch Path Risk F5/F6 or create a Path Risk rescue;
- create alpha+risk sizing/execution/PnL/paper/live logic;
- merge to `main`.

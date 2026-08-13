# Ranking V3-D PIT Sector Data-Gate Recheck — Blocked

Date: 2026-08-10 (Asia/Jakarta)
Status: **`BLOCKED_PIT_SECTOR_HISTORY`**
Branch: `research/idx-ranking-v2-spec-v1`
HEAD at review: `147b6a4f665ecfea9117b58f10c81bc5747fe034`

## Scope

This is the post-V3-C outcome-independent V3-D data-gate/prep review only.
V3-C is final `V3_C_REGIME_KILL_KEEP_V2_CONTROL`; no V3-C rescue was
attempted. V3-D remains exact V2 25 features plus the frozen six PIT
sector-relative features. `ranking_v3_sector_amended.py` remains an
evaluation-only wrapper. No V3-D scoring or outcome access was authorized.

## Preflight

- branch was fetched and already matched remote before work;
- working tree was clean before the review;
- full explicit IDX Trade pytest: `357 passed`, `0 failed`, `3 warnings`;
- pytest runtime: `15.77s`;
- wrapper runtime: `18.071s`;
- warnings are the existing pandas `FutureWarning` instances in curated
  identity and tradability-anchor tests.

## Frozen input verification

| Artifact | Resolved path | SHA-256 | Result |
|---|---|---|---|
| signal panel | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet` | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` | PASS |
| official calendar | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` | PASS |
| security master | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260.csv` | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` | PASS |
| V2 prepared table | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet` | `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5` | PASS |
| V2 prepared manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_cache_manifest.json` | `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143` | PASS |

The current V3-D spec SHA-256 is
`2ef5025ed10a761381e4e32964be9de51920e56e2fa249967b777bcbd9195194`; its
Git blob is `ca4ba61dc7ccb8b9ec878ce5b445dce20e0f8133`.

## PIT IDX-IC source inventory

No source passed the required immutable ticker-by-date PIT contract. The
following sources were checked or retained as leads:

| Source | What it establishes | Why it cannot clear V3-D | Source hash |
|---|---|---|---|
| Official IDX Stocks page, `https://www.idx.id/en/products/stocks/` | IDX-IC taxonomy and stated implementation start `2021-01-25` | current taxonomy page; no complete ticker interval/change history or immutable `available_at` per record | NOT VERIFIED AS IMMUTABLE SOURCE BYTES |
| Official IDX Stock List, `https://www.idx.id/en/market-data/stocks-data/stock-list/` | current sector/board filter entry point | dynamic current list; no historical effective/availability fields | NOT VERIFIED AS IMMUTABLE SOURCE BYTES |
| IDX monthly Digital Statistics stock-price listing used in the prior audit | report-month ticker/sector rows | report month is not an exact economic effective date and does not provide defensible public availability timestamp | NOT ACCEPTED FOR PIT |
| `Peng-00012/BEI.POP/01-2021` initial-list lead | possible initial 2021 constituent list | publicly indexed lead is not a verified first-party immutable byte source and does not cover subsequent listings/reclassifications | NOT VERIFIED |
| `D:\Documents\Project\idx-trade-external\Dataset-Saham-IDX\List Emiten\Sectors\*.csv` | current local sector snapshots | current-state snapshots; no official immutable source chain or historical change semantics | REJECTED / NOT USED |

The official IDX page states that IDX-IC began on 2021-01-25 and lists sectors
`A` through `K` plus `Z`. That taxonomy fact is insufficient to reconstruct the
complete ticker-level history across the development period
`2021-04-29..2026-07-31`. New listings, reclassifications, and interval end
dates require explicit source evidence. The `available_at` date needed by the
contract is also absent from the current/dynamic sources.

## PIT semantics and stop

The required normalized contract is:

```text
ticker
sector_code
effective_from
effective_to_exclusive
available_at
source_id
source_sha256
```

The required rule is:

```text
usable_from = max(effective_from, calendar_date(available_at))
```

Because a complete source chain for those dates and semantics was not
established, no rows were fabricated from current sector labels or assumed
report-month dates.

- `validate-history`: **NOT RUN**; no admissible sector-history file exists;
- `prepare`: **NOT RUN**;
- normalized-history SHA: **NONE**;
- sector-history SHA: **NONE ACCEPTED**;
- prepared-cache SHA: **NONE**;
- manifest SHA: **NONE**;
- F1-F4 assignment/finite/group diagnostics: **NOT GENERATED**;
- data-gate decision: **`BLOCKED_PIT_SECTOR_HISTORY`**.

## Boundary confirmation

- V3-D control/candidate were not fitted, scored, or summarized;
- zero V3-D outcome metrics were viewed;
- V2F5/V2F6 were not accessed;
- post-2026-07-31 fresh-forward outcomes were not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written;
- V3-E, integration, calibration, Stage 6, IDX-VAL-002, execution/PnL,
  paper/live, and main merge were not started.

## Next action

V3-D remains parked. It can resume only after an official immutable historical
IDX-IC archive or equivalent first-party source chain establishes every
required effective and availability semantic, passes independent hashing, and
is accepted by `validate-history`.

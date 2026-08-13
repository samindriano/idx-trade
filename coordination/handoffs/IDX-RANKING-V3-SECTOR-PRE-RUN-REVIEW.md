# Handoff — IDX Ranking V3-D Sector-Relative Pre-Run Data Gate

Date: 2026-08-10 (Asia/Jakarta)

Status: **POST-V3-C AMENDMENT FROZEN / DATA-GATE WORK ONLY — V3-D OUTCOME SCORING NOT AUTHORIZED**

## Objective

Complete only the outcome-independent V3-D pre-run work after V3-C review. V3-C is closed with `V3_C_REGIME_KILL_KEEP_V2_CONTROL`. The one allowed V3-C-informed V3-D amendment has already been frozen and implemented. Do not redesign V3-D and do not score it.

## Required reads

1. `docs/CURRENT_STATUS.md`
2. `docs/checkpoints/2026-08-10_RANKING_V3_REGIME_F1_F4_RESULT.md`
3. `docs/checkpoints/2026-08-10_RANKING_V3_REGIME_REVIEW_PASS_V3D_AMENDED.md`
4. `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_V1.md`
5. `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_REVIEW_ADDENDUM_V1.md`
6. `docs/RANKING_V3_SECTOR_RELATIVE_POST_V3C_AMENDMENT_V1.md`
7. `docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PROVISIONAL_IMPLEMENTED.md`
8. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
9. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`
10. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`
11. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
12. `src/idx_trade/research_v3_sector.py`
13. `src/idx_trade/ranking_v3_sector.py`
14. `src/idx_trade/ranking_v3_sector_amended.py`
15. `tests/test_ranking_v3_sector.py`
16. `tests/test_ranking_v3_sector_amended.py`

## Final pre-outcome V3-D hypothesis

Candidate remains unchanged:

- ordinal 008: exact V2 `HGB_XS_MARKET` control;
- ordinal 009: exact V2 25 features + exactly six PIT sector-relative features;
- one global HGB only.

Six features:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

No Structure-Lite feature, regime feature, regime router, regime expert, rescaling, blending, or fallback is allowed.

## Frozen post-V3-C evaluation amendment

The V3-C regime cache is now a diagnostic partition only, pinned by SHA-256:

`1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`

When V3-D is eventually outcome-authorized, the controlling run must use `idx_trade.ranking_v3_sector_amended`, not the base runner alone.

The amended final promotion requires original V3-D gates plus:

- NORMAL median paired PR improvement >= `-0.005`;
- STRESS median paired PR improvement >= `-0.005`;
- NORMAL/STRESS median ROC change each >= `-0.005`;
- NORMAL/STRESS median Q5-Q1 change each >= `-0.005`;
- worst fold/state PR improvement >= `-0.015`.

Top-decile lift remains diagnostic only.

**Do not run these outcome metrics in this handoff.**

## Phase A — full pytest on amended tree

From the explicit IDX Trade repo root run the full repository suite and record pass/fail/warnings/duration.

The last known merged-tree baseline before the new amendment commits was `277 passed, 0 failed, 3 warnings`. The amended tree must be revalidated; do not assume that result carries forward.

If tests fail, fix engineering defects only. Do not alter the six features, PIT rules, thresholds, or post-V3-C guard without returning to ChatGPT first.

## Phase B — locate/build real PIT sector-history artifact

Do not fabricate historical membership from a current-sector snapshot.

Required columns:

- `ticker`
- `sector_code`
- `effective_from`
- `effective_to_exclusive`
- `available_at`
- `source_id`
- `source_sha256`

`usable_from = max(effective_from, calendar_date(available_at))`.

For each unique `(source_id, source_sha256)`, independently verify actual immutable source bytes or a trusted immutable archive identity. Record source location/archive identity, taxonomy/version, effective/availability semantics, and hash verification.

If a defensible PIT history cannot be established, record `BLOCKED_PIT_SECTOR_HISTORY` and STOP. Do not backfill current IDX-IC labels.

## Phase C — PIT validator

Run the existing `idx_trade.ranking_v3_sector validate-history` command using the frozen security master and a new empty output directory.

Fail closed on:

- invalid interval dates;
- overlap;
- classification not yet available;
- untraceable ticker/security identity;
- inconsistent duplicate metadata;
- invalid/unverified source provenance.

Return normalized-history hash and provenance inventory.

## Phase D — outcome-independent cache prepare

Only after PIT history is defensible, run:

`python -m idx_trade.ranking_v3_sector prepare ...`

using exact frozen panel/calendar/security master/V2 prepared table/V2 manifest, the V3-D spec, and a new empty output directory.

Required gate for **every** V2F1-V2F4 train and validation block:

- PIT sector assignment >=90%;
- every one of six sector features finite >=80%;
- validation contains >=8 represented sectors;
- exact recomputed V2 25-feature equality <=1e-12;
- no invalid assignment or silent row drop;
- max materialized signal session <=984;
- V2F5/V2F6 not materialized;
- outcome metrics not computed.

Report group-size distribution and rows failing the minimum-five-finite-members rule.

If any mandatory data/coverage gate fails, record `V3_D_SECTOR_BLOCKED_KEEP_V2_CONTROL` and STOP. Do not weaken thresholds or change sector taxonomy to rescue coverage.

## Phase E — stop for final authorization

Do **not** call either:

- `python -m idx_trade.ranking_v3_sector run`
- `python -m idx_trade.ranking_v3_sector_amended ...`

No `V3_D_OUTCOME_RUN_AUTHORIZED` JSON exists yet.

Return to ChatGPT with:

- branch + final HEAD + clean/synced status;
- full amended-tree pytest result;
- sector-history source SHA and normalized-history SHA;
- source-document/archive hash-verification inventory;
- sector taxonomy/version and effective/availability semantics;
- PIT assignment coverage per F1-F4 train/validation;
- six-feature finite coverage per fold/block;
- distinct sectors and group-size diagnostics;
- V3-D prepared cache + manifest SHA;
- exact V2 recomputation max diff;
- confirmation V3-D outcomes were not viewed;
- confirmation F5/F6 and post-2026-07-31 fresh-forward outcomes were not accessed.

ChatGPT will then independently review the data gate and, only if defensible, create/freeze the final authorization identities and outcome-run handoff.

## Hard prohibitions

Do not:

- rescue/reopen V3-C;
- change V3-C regime thresholds;
- add regime experts to V3-D;
- change V3-D six-feature candidate;
- score V3-D without final authorization;
- use current-sector historical backfill;
- weaken group-size/coverage gates;
- access V2F5/V2F6;
- access reserved V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-E/integration/calibration/Stage6/IDX-VAL-002/execution/PnL/Kelly/paper/live/main automatically.

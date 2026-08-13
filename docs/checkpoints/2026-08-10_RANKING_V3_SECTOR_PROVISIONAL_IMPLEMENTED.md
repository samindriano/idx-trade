# Ranking V3-D Sector-Relative — Provisional Implementation Checkpoint

Date: 2026-08-10 (Asia/Jakarta)

Status: **IMPLEMENTED PRE-OUTCOME BASELINE — NOT AUTHORIZED TO SCORE**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

## Decision

V3-D engineering has been advanced asynchronously while the separately frozen V3-C local run is pending. No V3-D outcome has been viewed and no PIT sector data gate has been claimed PASS.

The provisional discovery question remains:

> Does a compact six-feature point-in-time sector-relative representation add robust ranking information beyond the exact global V2 `HGB_XS_MARKET` control?

## Frozen/provisional candidate shape

Provisional ordinals:

- `008`: exact V2 `HGB_XS_MARKET` control;
- `009`: exact V2 25 features plus six sector-relative features.

Six sector features:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

The candidate does not inherit Structure-Lite or Regime. This preserves hypothesis attribution; any later stacking remains a separate integration experiment.

## Implementation lineage

Specification baseline:

- `670a4cbc7c9fdc98eb3d82dfc336a7b23624d8a0` — provisional V3-D pre-outcome spec.

Implementation:

- `ae8dcfe91e4656d4f8536d0fcf1f7fd7575ecb92` — PIT sector-history validator, assignment, and six-feature builder;
- `ca658e13d0d3ad4333820cab7ba9d2ef766c8ffc` — F1-F4-only cache preparation, guarded runner, control-equivalence path, and sector diagnostics;
- `28981a25a427f67db0fc940415d0d7c910a9ff84` — focused PIT/feature/run-authorization tests;
- `600c439c42e2a4452859ea7354e41d246db1e42e` — pre-outcome PIT validation/dtype/schema hardening.

Review addendum:

`docs/RANKING_V3_SECTOR_RELATIVE_SPEC_REVIEW_ADDENDUM_V1.md`

- source-provenance hashes must be independently evidenced before final data-gate PASS;
- one V3-C-informed, outcome-blind amendment is permitted before the first V3-D outcome run;
- preferred amendment scope is diagnostics/guardrails, not silent inheritance of V3-C architecture.

## PIT sector-history contract

A usable historical sector artifact must contain:

- `ticker`;
- `sector_code`;
- `effective_from`;
- `effective_to_exclusive`;
- `available_at`;
- `source_id`;
- `source_sha256`.

For every interval:

`usable_from = max(effective_from, calendar_date(available_at))`.

No current classification may be backfilled before `usable_from`. Missing history remains missing. Overlapping usable intervals, untraceable tickers, invalid interval dates, inconsistent duplicates, and invalid source hashes fail closed.

Every referenced `(source_id, source_sha256)` must later be tied to actual immutable source bytes or a trusted immutable archive identity and independently verified before run authorization.

## Outcome-independent cache contract

The implemented prepare path:

1. verifies pinned panel/calendar/security-master/V2 prepared artifacts;
2. bounds raw feature construction at official signal session 984;
3. rebuilds baseline/V2 features from the full causal primary-liquid frame;
4. assigns PIT sector membership;
5. computes sector ranks/medians across all eligible same-date sector members, not label-resolved rows only;
6. requires at least five finite sector members per source concept;
7. physically loads only V2 prepared rows through session 984;
8. proves exact recomputed V2 25-feature equality at `1e-12`;
9. preserves exact V2 row/order/labels;
10. writes coverage/provenance/group diagnostics and an immutable discovery cache.

Pre-score gate for every F1-F4 train/validation block:

- sector assignment >=90%;
- each of six features finite >=80%;
- validation contains >=8 sectors;
- no invalid assignment or row drop.

Failure yields `V3_D_SECTOR_BLOCKED_KEEP_V2_CONTROL` before model outcomes.

## Outcome-run guard

Although the runner implementation exists, the `run` command requires a separate authorization JSON with status:

`V3_D_OUTCOME_RUN_AUTHORIZED`

and pinned final identities for:

- completed independent V3-C review;
- final V3-D spec;
- final V3-D cache;
- final cache manifest;
- implementation commit.

No such authorization exists yet. Therefore V3-D scoring is fail-closed.

## Tests / runtime status

Focused tests have been written in `tests/test_ranking_v3_sector.py`, including no-backfill, overlap, source SHA, group-size, sector-rank/median, frozen HGB parameters, F5/F6 block, coverage failure, and separate run authorization.

**No local/full pytest result is claimed from the ChatGPT runtime.** The repository/local operator must run full pytest before any future V3-D data preparation or outcome authorization.

## Current blockers

1. V3-C result has not yet returned for independent review.
2. A real historical PIT sector artifact has not yet been validated.
3. Its referenced source documents/snapshots have not yet been independently hash-verified.
4. The F1-F4 sector coverage gate has therefore not yet run on real data.
5. No final V3-D cache/run authorization exists.

Cumulative evaluated V3 candidate count remains `5`. Provisional ordinals 008/009 are not evaluated candidates.

## Safety boundary

Do not:

- score V3-D yet;
- use a current-sector snapshot as historical backfill;
- alter the six-feature candidate based on V3-D outcomes;
- load/score/summarize V2F5/V2F6;
- access reserved post-2026-07-31 V2 forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-E/integration/calibration/Stage 6/IDX-VAL-002/execution-PnL/paper/live/main automatically.

Next decision point: receive and review V3-C, then decide whether the allowed one-time pre-outcome V3-D amendment is useful before locating/validating PIT sector history.

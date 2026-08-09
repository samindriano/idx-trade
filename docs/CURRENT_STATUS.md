# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the short **authoritative first-read status layer**. For full chronology read `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest checkpoint. If an older current-stage paragraph conflicts with this file, this file plus the newest dated checkpoint controls the current phase and authorization boundary.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1` / draft PR #10;
- separate runtime-performance branch: `perf/idx-research-runtime-v1` / PR #9;
- Ranking V1: **FAILED benchmark**;
- Stage-5 holdout: **consumed for `RANKING_V1_ONLY`; never rerun**;
- Probability V1: **`PROBABILITY_V1_NOT_READY_DEFERRED`**;
- performance equivalence: **PASS — `FULL_PANEL_LEGACY_FAST_EQUIVALENT`**;
- immutable Ranking-V2 prepared cache: **FROZEN**;
- V2 control + A/B/C/D candidate orchestra: **COMPLETE**;
- metrics-only integration: **`RANKING_V2_HISTORICAL_CHAMPION_SELECTED`**;
- historical-development champion: **`HGB_XS_MARKET`**;
- independent ChatGPT champion review: **PASS**;
- current authorization: **champion and final-refit/fresh-forward contract frozen; final refit and fresh-forward outcome evaluation are not yet authorized**;
- Stage 6: not authorized;
- `IDX-VAL-002`: not started;
- execution-PnL / paper / live trading: not authorized;
- merge to `main`: not authorized.

Newest controlling checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V2_HISTORICAL_CHAMPION_REVIEW.md`

Next handoff:

`coordination/handoffs/IDX-RANKING-V2-CHAMPION-FREEZE-FORWARD-SPEC.md`

Mandatory first-read before any **next model / next research-generation / optimized fresh-forward runtime implementation**:

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`

The implementing agent must explicitly confirm it read that note before changing or creating the next model/runtime implementation.

## Data foundation

Signal-research HLCV 1260 is GO:

- exact window `2021-04-29 -> 2026-07-31`;
- 979 required common stocks;
- 981,940 ACTIVE research rows;
- H/L/C/Volume complete on included contract rows;
- Open nullable and never synthesized;
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- manifest SHA-256: `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`;
- official-calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security-master SHA-256: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Strict execution-grade 1260 remains FAIL because historical Open evidence is incomplete. Do not conflate Signal-Research GO with strict execution-grade PASS.

## V1 chronology

- Stage 2: frozen causal research/validation contract;
- Stage 3: HGB showed modest development ranking edge;
- Stage 4: ranking robustness retained, calibration blocked;
- Stage 4B: causal calibration attempt also blocked;
- Probability V1 permanently deferred;
- Stage 5: one-shot ranking-only holdout **FAIL**.

Stage-5 H10 summary:

- base/prevalence `0.4071688603`;
- HGB PR-AUC `0.4073793720`, delta `+0.0002105118`;
- HGB ROC-AUC `0.4948433255`;
- HOLDOUT_A retained modest edge;
- HOLDOUT_B reversed below base / ROC<0.5;
- H5/H20 were near-null and cannot rescue V1.

The Stage-5 holdout is permanently consumed.

## Ranking V2 — frozen design

Frozen substantive implementation code head:

`5f2ed2f53aececfd7c338d3f9f65db1efae372b6`

Frozen feature families:

- 10 same-date primary-universe percentile-rank stock features;
- 9 continuous causal market-state context features;
- 6 stock-minus-market-median relative features;
- no sector-relative features until a PIT-safe historical sector mapping exists.

Frozen candidates:

- non-eligible control: `V1_HGB_CONTROL`;
- V2-A: `LOGISTIC_XS`;
- V2-B: `HGB_XS`;
- V2-C: `HGB_XS_MARKET`;
- V2-D: `PAIRWISE_LOGISTIC_XS`.

Historical-development validation used six expanding chronological folds, each with an exact 20-session gap and a 100-session validation block. Selection was H10-only under the predeclared robustness-first eligibility/tie-break rules.

All history through `2026-07-31` is development/research knowledge. No historical V2 result can be upgraded to independent validation after the fact.

## Performance-equivalence result

Performance runtime HEAD:

`4f1f3af2c71cb49df7249a11d0c684cfef4aa9ca`

Repo-local pytest: **218 passed, 3 warnings**.

Result:

- status `FULL_PANEL_LEGACY_FAST_EQUIVALENT`;
- `legacy_fast_equal=true`;
- horizons `[5, 10, 20]`;
- H5 legacy `1567.8568 s`;
- H10 legacy `1559.6417 s`;
- H20 legacy `1592.5304 s`;
- fast multi-horizon `16.2132 s`;
- approximate benchmark label-engine speedup vs parallel legacy wall estimate: `98.22x`;
- equivalence report SHA-256: `8f8865b2f133020a94ab8d2507fbb221f4b7f59bd1775b9da51fba2f4084d554`;
- exact fast-H10 SHA-256: `a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`.

The speedup is specifically a label-engine benchmark result, not a guaranteed end-to-end candidate speedup.

## Immutable Ranking-V2 prepared cache

Manifest status:

`RANKING_V2_PREPARED_CACHE_FROZEN`

Prepared cache:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet`

SHA-256:

`522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`

Facts:

- rows `292633`;
- tickers `737`;
- signal-session index `20..1250`;
- positive rate `0.3939849573`;
- resolved primary H10 model rows only.

Manifest SHA-256:

`6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`

## Ranking-V2 historical-development result

All five frozen tasks completed and all 50 candidate artifacts were independently hash-verified with zero mismatches.

Champion:

`HGB_XS_MARKET`

Key aggregate facts:

- median PR-AUC delta `0.0238795`;
- q25 PR-AUC delta `0.0194015`;
- positive PR-delta folds `6/6`;
- median ROC-AUC `0.524410`;
- ROC-AUC >0.5 folds `5/6`;
- positive Q5-Q1 folds `6/6`;
- worst-fold PR-delta `0.008789`.

Versus the non-eligible V1 control, the champion improves median PR-delta by only about `+0.0015315`, but improves q25 PR-delta by about `+0.0025528`, median ROC by `+0.005400`, median Q5-Q1 by about `+0.0201875`, and worst-fold PR-delta from `0.000785` to `0.008789`.

Interpretation: evidence supports improved historical-development robustness from cross-sectional + explicit market-context features, but not a claim of overwhelming superiority. V2F6 ROC-AUC remained below 0.5 (`0.493102`) despite positive PR-delta and Q5-Q1, so fresh-forward validation is essential.

Integrator summary SHA-256:

`3facb4468caafab8cf19f368cf5ef04f36dac052089d2ecb810b683c851ec705`

## Champion-freeze / forward-spec result

The champion-freeze / forward-spec task is complete on this branch. The
reviewable contract is:

`docs/RANKING_V2_CHAMPION_FORWARD_SPEC_V1.md`

Checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V2_CHAMPION_FORWARD_SPEC_FROZEN.md`

No fresh-forward outcomes were inspected. The next action requires MAIN /
ChatGPT review and explicit authorization to implement the final-refit and
one-shot fresh-forward runtime against the frozen contract.

## Authorization boundary

Do not:

- rerun Stage 5;
- reopen/tune/rescue Ranking-V2 candidate selection;
- modify the selected champion based on historical outcomes now observed;
- use H5/H20 to rescue the champion;
- call history through `2026-07-31` independent V2 validation;
- inspect fresh-forward outcomes before the forward contract is frozen;
- start probability calibration;
- start Stage 6;
- run `IDX-VAL-002`;
- make execution-PnL claims;
- Kelly-size;
- paper/live trade;
- merge to `main`.

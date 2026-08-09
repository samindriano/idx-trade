# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the short **authoritative first-read status layer**. For full chronology read `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest checkpoint. If an older current-stage paragraph conflicts with this file, this file plus the newest dated checkpoint controls the current phase and authorization boundary.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1` / draft PR #10;
- separate runtime-performance branch: `perf/idx-research-runtime-v1` / PR #9;
- Ranking V1: **FAILED benchmark**;
- Stage-5 holdout: **consumed for `RANKING_V1_ONLY`; never rerun**;
- Probability V1: **`PROBABILITY_V1_NOT_READY_DEFERRED`**;
- Stage-5 bounded post-mortem: complete and independently interpreted;
- Ranking-V2 specification and implementation: **frozen before V2 outcomes**;
- performance equivalence: **PASS — `FULL_PANEL_LEGACY_FAST_EQUIVALENT`**;
- immutable Ranking-V2 prepared cache: **FROZEN**;
- ChatGPT cache/equivalence review: **PASS**;
- current authorization: **run frozen V1 control + V2-A/B/C/D historical-development candidate orchestra, then metrics-only integration**;
- Ranking-V2 candidate outcomes: **not yet reviewed / do not alter definitions once execution begins**;
- Stage 6: not authorized;
- `IDX-VAL-002`: not started;
- execution-PnL / paper / live trading: not authorized;
- merge to `main`: not authorized.

Newest controlling checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V2_CACHE_FROZEN_CANDIDATES_AUTHORIZED.md`

Runtime handoff:

`coordination/handoffs/IDX-RANKING-V2-CANDIDATE-ORCHESTRA-RUNTIME.md`

Mandatory first-read before any **next model / next research-generation / optimized fresh-forward runtime implementation**:

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`

The implementing agent must explicitly confirm it read that note before changing or creating the next model/runtime implementation. The note is not authorization to modify the currently running frozen V2 control/A/B/C/D experiment.

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

## Post-mortem interpretation

Bounded evidence supports a **regime/covariate-shift hypothesis** more than a hypothesis that all structure information disappeared. Key descriptive facts include large A→B shifts in ATR/Close, breadth and market returns, while several structure relationships retained direction. `observed_session_count` and `security_age_sessions_exact` are excluded from V2 core because they can act as mechanically drifting time/era proxies.

These findings are design hypotheses, not independent causal/predictive claims.

## Ranking V2 — frozen design

Frozen substantive implementation code head:

`5f2ed2f53aececfd7c338d3f9f65db1efae372b6`

Frozen feature families:

- 10 same-date primary-universe percentile-rank stock features;
- 9 continuous causal market-state context features;
- 6 stock-minus-market-median relative features;
- no sector-relative features until a PIT-safe historical sector mapping exists.

Frozen models:

- non-eligible control: `V1_HGB_CONTROL`;
- V2-A: `LOGISTIC_XS`;
- V2-B: `HGB_XS`;
- V2-C: `HGB_XS_MARKET`;
- V2-D: `PAIRWISE_LOGISTIC_XS`.

Frozen validation uses six expanding chronological folds, each with an exact 20-session gap and a 100-session validation block. Candidate selection is H10-only and robustness-first under the predeclared eligibility/tie-break rules. If no candidate qualifies, the result is `RANKING_V2_NO_CHAMPION`.

All history through `2026-07-31` is development/research knowledge. Any selected model is only a historical-development champion. Independent V2 validation requires fresh forward data strictly after `2026-07-31`, after the champion architecture is frozen.

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

All candidate workers must treat this cache as immutable/read-only and verify the exact SHA before outcome computation.

## Immediate next action

Run the frozen candidate orchestra according to:

`coordination/handoffs/IDX-RANKING-V2-CANDIDATE-ORCHESTRA-RUNTIME.md`

Assignments:

1. `V1_HGB_CONTROL` comparator;
2. `LOGISTIC_XS`;
3. `HGB_XS`;
4. `HGB_XS_MARKET`;
5. `PAIRWISE_LOGISTIC_XS`.

All five may use isolated parallel workers against the same cache. If all complete successfully, run the existing metrics-only integrator and apply the frozen champion-selection rules. Stop after the historical-development champion/no-champion result and return to ChatGPT for independent review.

## Authorization boundary

Do not:

- rerun Stage 5;
- tune/rescue Ranking V1 against consumed outcomes;
- modify V2 candidate definitions/features/folds/hyperparameters after outcomes begin;
- use H5/H20 to select or rescue a V2 candidate;
- call history through `2026-07-31` independent V2 validation;
- start probability calibration;
- start Stage 6;
- run `IDX-VAL-002`;
- make execution-PnL claims;
- Kelly-size;
- paper/live trade;
- merge to `main`.

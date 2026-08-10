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
- Ranking-V2 historical-development champion: **`HGB_XS_MARKET`**;
- V2 final refit + outcome-blind forward runtime: **IMPLEMENTED/FROZEN**;
- actual V2 fresh-forward outcome access: **BLOCKED pending separate one-shot authorization and 100 H10-mature sessions**;
- Ranking V3 roadmap: **AUDITED after legacy-model autopsy**;
- Ranking V3-A recency spec: **INDEPENDENT REVIEW PASS WITH PRE-OUTCOME ADDENDUM**;
- Ranking V3-A runner: **IMPLEMENTED**;
- Ranking V3-A F1-F4 outcome run: **COMPLETE — control-equivalence PASS; both recency variants KEEP_DIAGNOSTIC; V2 control retained**;
- Ranking V3 V2F5/V2F6: **SEALED FOR FUTURE FINAL-V3 LATE-DEVELOPMENT CONFIRMATION**;
- reserved post-2026-07-31 V2 forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- Stage 6 / `IDX-VAL-002` / probability calibration / execution-PnL / paper/live / main merge: **NOT AUTHORIZED**.

Newest implementation checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_RUNNER_IMPLEMENTED_DATA_BLOCKED.md`

Current implementation/result handoff:

`coordination/handoffs/IDX-RANKING-V3-RECENCY-RUNNER-IMPLEMENTED-DATA-BLOCKED.md`

Controlling V3-A execution authorization:

`coordination/handoffs/IDX-RANKING-V3-RECENCY-DISCOVERY-RUN.md`

Mandatory first-read before any next model/runtime implementation:

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`

Mandatory V3 research reads:

- `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
- `docs/RANKING_V3_RESEARCH_BACKLOG.md`;
- `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`;
- `docs/RANKING_V3_RECENCY_SPEC_V1.md`;
- `docs/RANKING_V3_RECENCY_SPEC_REVIEW_ADDENDUM_V1.md`;
- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`.

The review addendum controls wherever it conflicts with the original recency spec.

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

## Ranking V2 — frozen design and result

Frozen substantive implementation code head:

`5f2ed2f53aececfd7c338d3f9f65db1efae372b6`

Frozen V2 feature families:

- 10 same-date primary-universe percentile-rank stock features;
- 9 continuous causal market-state context features;
- 6 stock-minus-market-median relative features;
- no sector-relative features until PIT-safe historical sector mapping exists.

Frozen candidates were:

- non-eligible control `V1_HGB_CONTROL`;
- `LOGISTIC_XS`;
- `HGB_XS`;
- `HGB_XS_MARKET`;
- `PAIRWISE_LOGISTIC_XS`.

Historical-development validation used six expanding chronological folds, exact 20-session gaps, 100-session validation blocks, H10-only selection and robustness-first frozen gates.

Selected champion:

`HGB_XS_MARKET`

Key historical-development facts:

- median PR-AUC delta `0.0238795`;
- q25 PR-AUC delta `0.0194015`;
- positive PR-delta folds `6/6`;
- median ROC-AUC `0.524410`;
- ROC-AUC >0.5 folds `5/6`;
- positive Q5-Q1 folds `6/6`;
- worst-fold PR-delta `0.008789`;
- V2F6 ROC-AUC `0.493102` despite positive PR-delta/Q5-Q1.

Integrator summary SHA-256:

`3facb4468caafab8cf19f368cf5ef04f36dac052089d2ecb810b683c851ec705`

All history through `2026-07-31` is development/research knowledge, not independent V2 validation.

## Performance-equivalence result

Performance runtime HEAD:

`4f1f3af2c71cb49df7249a11d0c684cfef4aa9ca`

Result:

- `FULL_PANEL_LEGACY_FAST_EQUIVALENT`;
- H5 legacy `1567.8568 s`;
- H10 legacy `1559.6417 s`;
- H20 legacy `1592.5304 s`;
- fast multi-horizon `16.2132 s`;
- label-engine benchmark speedup `98.22x`;
- equivalence report SHA-256 `8f8865b2f133020a94ab8d2507fbb221f4b7f59bd1775b9da51fba2f4084d554`;
- exact fast-H10 SHA-256 `a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`.

This is a label-engine benchmark, not a guaranteed end-to-end candidate speedup.

## Immutable Ranking-V2 prepared cache

Prepared table:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet`

Prepared-table SHA-256:

`522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`

Prepared-cache manifest SHA-256:

`6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`

Facts:

- 292,633 rows;
- 737 tickers;
- signal-session index `20..1250`;
- positive rate `0.3939849573`;
- resolved primary H10 rows only.

## V2 final refit / fresh-forward contract

Controlling specification:

`docs/RANKING_V2_CHAMPION_FORWARD_SPEC_V1.md`

Reviewed spec blob:

`77b2d74c9d5f28460037c11cd3a134c6b6cc9d3d`

Final refit result:

- final model SHA-256 `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace`;
- model manifest SHA-256 `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9`;
- 292,633 rows / 737 tickers / sessions `20..1250`;
- fresh-forward outcomes not accessed;
- global marker not written.

First independent V2 verdict remains exactly 100 consecutive mature forward signal sessions, with first-50/last-50 stability and the frozen PASS/MIXED/FAIL semantics. Q5-Q1 means `Q5 TP rate - Q1 TP rate`, not realized-return spread.

## Ranking V3 roadmap

After the legacy archive audit, the current V3 hypothesis order is:

1. V3-A RECENCY;
2. V3-B STRUCTURE-LITE;
3. V3-C REGIME-SPECIALIZATION;
4. V3-D SECTOR-RELATIVE, conditional on a PIT-safe sector data gate;
5. V3-E TRUE-RANKING.

Distributional uncertainty, path-risk, broker flow, EventRank, fundamentals and broader macro inputs remain separate future lanes, not first-pass V3 feature soup.

Global V3 rules:

- one falsifiable hypothesis per experiment;
- exact V2 champion control;
- normally control + at most two bounded variants;
- permanent candidate/hypothesis denominator;
- robustness-first metrics, not best-period optimization;
- no post-result rescue under the same hypothesis;
- at most one later preregistered integration experiment;
- V2F5/V2F6 reserved once for final-V3 late-development confirmation;
- reserved V2 fresh-forward outcomes remain unavailable to V3 R&D.

## Ranking V3-A RECENCY — effective frozen contract

Original spec:

`docs/RANKING_V3_RECENCY_SPEC_V1.md`

Reported spec SHA-256:

`53c5bc3e90af12fea62a73815e1e85352e836d69938ce0e9287437a52c1d58fa`

Review addendum:

`docs/RANKING_V3_RECENCY_SPEC_REVIEW_ADDENDUM_V1.md`

Frozen candidates:

- `V3-A-RECENCY-V1-CONTROL-001`: exact uniform V2 `HGB_XS_MARKET`;
- `V3-A-RECENCY-V1-HL252-002`: H=252 official sessions;
- `V3-A-RECENCY-V1-HL504-003`: H=504 official sessions.

Only sample weights may differ:

`age = train_end - signal_session_index`

`raw_weight = 2 ** (-age / H)`

Weights are normalized fold-locally to arithmetic mean 1.0. Label, universe, exact 25 features, HGB architecture/parameters, ranking score and metric semantics stay unchanged.

Authorized discovery folds:

- V2F1/V3D1;
- V2F2/V3D2;
- V2F3/V3D3;
- V2F4/V3D4.

V2F5/V2F6 must not be scored or summarized for V3-A.

## Ranking V3-A runner implementation result

Implementation code:

`src/idx_trade/ranking_v3_recency.py`

Focused tests:

`tests/test_ranking_v3_recency.py`

Implementation lineage:

- `cab1ad4f0a78bcee63ac75d10997fef1f1122f85` — initial runner;
- `57f2b955bee3b48ace31f7eb22327e8d224adef0` — focused tests;
- `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f` — final sealed-reference-path implementation fix.

Implemented guardrails include:

- exact prepared-cache/manifest hash verification;
- frozen spec SHA/Git-blob verification and review-addendum Git-blob verification;
- V2F1-F4-only scoring loop;
- explicit V2F5/V2F6 rejection;
- exact uniform-control fit first;
- SHA-verified frozen V2 HGB_XS_MARKET reference summary/prediction artifact;
- Parquet predicate materialization of only F1-F4 reference rows;
- mandatory row/score/metric equivalence before H252/H504 can fit;
- sequential reference execution;
- frozen discovery gates/tie rule;
- hashed metrics/predictions/models/runtime/verdict/ledger artifacts.

Focused isolated ChatGPT-runtime harness result:

**12 passed in 0.63 s**

This was not the repo-local full pytest suite. GitHub did not expose an automatic workflow run for these commits.

The local F1-F4 discovery run is complete against the exact frozen Windows artifacts:

- repo pytest: `240 passed, 3 warnings` in `19.04 s`;
- control equivalence: **PASS**, `84,732` rows, maximum score difference `0.0`, and maximum difference `0.0` for every required metric;
- H=252: absolute sanity **PASS**, paired promotion **FAIL**, verdict `KEEP_DIAGNOSTIC`;
- H=504: absolute sanity **PASS**, paired promotion **FAIL**, verdict `KEEP_DIAGNOSTIC`;
- deterministic result: `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`;
- selected/promoted recency component: none;
- runtime: sequential reference, `40.3661506 s` total;
- output: `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_recency_discovery_20260810_retry1`;
- summary SHA-256: `cf5d50c746ba9d88c74303193f770817588d6ad0fd23f24bb34baeb162e7519f`.

The run scored only V2F1-V2F4. V2F5/V2F6 remained sealed, the reserved
post-2026-07-31 V2 forward outcomes were not accessed, and
`FORWARD_OUTCOME_ACCESS_STARTED` was not written by this run. The complete
result, metrics, paired diagnostics, provenance, and artifact inventory are in
`docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_F1_F4_RESULT.md`.

## Immediate next action

### V2 track

Wait. Do not access the fresh-forward block until the separately authorized first 100 mature forward signal sessions exist with immutable provenance.

### V3 track

The authorized V3-A F1-F4 discovery run is complete and documented. Stop for
ChatGPT review. Do not proceed automatically to Structure-Lite, F5/F6, or any
later V3 lane.

Do **not** proceed automatically to Structure-Lite after the run.

## Authorization boundary

Do not:

- rerun Stage 5;
- reopen/tune/rescue Ranking V2;
- call pre-2026-07-31 history independent validation;
- inspect reserved post-2026-07-31 V2 fresh-forward outcomes before separate one-shot authorization;
- write `FORWARD_OUTCOME_ACCESS_STARTED` before that authorization;
- score/load/summarize V2F5/V2F6 for V3-A;
- change V3-A half-lives, features, model parameters, gates or tie rule based on outcomes;
- start V3-B or later outcome work without a separately reviewed spec;
- start V3 integration/final confirmation;
- start probability calibration, Stage 6 or `IDX-VAL-002`;
- make execution-PnL claims;
- Kelly-size;
- paper/live trade;
- merge to `main`.

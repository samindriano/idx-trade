# IDX Trade — Current Status

Date: 2026-08-09 (Asia/Jakarta)

This is the short **authoritative first-read status layer**. For full chronology
read `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest
checkpoint. If an older current-stage paragraph conflicts with this file, this
file plus the newest dated checkpoint controls the current phase and
authorization boundary.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1` / draft PR #10;
- separate runtime-performance branch: `perf/idx-research-runtime-v1` / PR #9;
- Ranking V1: **FAILED benchmark**;
- Stage-5 holdout: **consumed for `RANKING_V1_ONLY`; never rerun**;
- Probability V1: **`PROBABILITY_V1_NOT_READY_DEFERRED`**;
- Stage-5 bounded post-mortem: complete and independently interpreted;
- Ranking-V2 specification: **frozen before V2 outcome runs**;
- Ranking-V2 candidate implementation: **ready**;
- current gate: **one-time full-panel legacy-vs-fast label equivalence benchmark, then immutable prepared-cache freeze**;
- Ranking-V2 candidate outcomes: **not run yet**;
- Stage 6: not authorized;
- `IDX-VAL-002`: not started;
- execution-PnL / paper / live trading: not authorized;
- merge to `main`: not authorized.

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

Strict execution-grade 1260 remains FAIL because historical Open evidence is
incomplete. Do not conflate Signal-Research GO with strict execution-grade PASS.

## V1 chronology

- Stage 2: frozen causal research/validation contract;
- Stage 3: HGB showed modest development ranking edge;
- Stage 4: ranking robustness retained, calibration blocked;
- Stage 4B: causal calibration attempt also blocked;
- Probability V1 permanently deferred;
- Stage 5: one-shot ranking-only holdout **FAIL**.

Stage-5 H10 summary:

- base/prevalence `0.4071688603`;
- HGB PR-AUC `0.4073793720`, delta only `+0.0002105118`;
- HGB ROC-AUC `0.4948433255`;
- HOLDOUT_A retained modest edge;
- HOLDOUT_B reversed below base / ROC<0.5;
- H5/H20 were near-null and cannot rescue V1.

The holdout is permanently consumed.

## Post-mortem interpretation

Read:

- `docs/checkpoints/2026-08-09_STAGE5_POSTMORTEM_RUNTIME.md`;
- `docs/checkpoints/2026-08-09_STAGE5_POSTMORTEM_INTERPRETATION.md`.

Bounded evidence supports a **regime/covariate-shift hypothesis** more than a
hypothesis that all structure information disappeared. Key descriptive facts:

- A→B median ATR/Close SMD `+2.2328`;
- breadth-return-20-positive SMD `-1.0093`;
- median-return-20 SMD `-1.0206`;
- B2/B3 ranking metrics turned negative;
- several structure relationships retained direction across A/B;
- top-decile enrichment existed in A and disappeared in B;
- `observed_session_count` and `security_age_sessions_exact` can act as
  mechanically drifting time/era proxies and are excluded from V2 core.

These findings are design hypotheses, not independent causal/predictive claims.

## Ranking V2 — frozen design

Read `docs/RANKING_V2_RESEARCH_SPEC_V1.md` and
`docs/checkpoints/2026-08-09_RANKING_V2_IMPLEMENTATION_READY.md`.

Substantive implementation HEAD:

`5f2ed2f53aececfd7c338d3f9f65db1efae372b6`

GitHub CI: **224 passed, 0 failed**.

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

Frozen historical-development validation:

- six expanding chronological folds;
- each has an exact H20 20-session gap;
- each validation block is 100 sessions;
- selection is robustness-first using median PR-AUC delta, positive-fold counts,
  ROC-AUC stability, Q5-Q1 stability, and a predeclared tie-break sequence;
- if no candidate passes the eligibility gate, result is
  `RANKING_V2_NO_CHAMPION`.

Any selected model is only a **historical-development champion**. Because the
Stage-5 outcomes informed V2 design, all history through `2026-07-31` is now
research/development knowledge. Independent V2 validation requires fresh
forward data strictly after `2026-07-31`, after the champion is frozen.

## Runtime-performance track

Branch `perf/idx-research-runtime-v1`, PR #9.

Substantive performance HEAD:

`9d8c59b05a293bcb64d3391b939ddcc63b46f717`

CI: **218 passed, 0 failed**.

The vectorized candidate computes ATR once and reuses one future-path scan for
H5/H10/H20. A one-time full-panel benchmark now exists and runs legacy H5/H10/H20
in three isolated processes in parallel, then the fast multi-horizon engine,
and compares all frozen semantic outputs.

Required pass status:

`FULL_PANEL_LEGACY_FAST_EQUIVALENT`

Legacy remains authoritative until this local full-panel equivalence passes.

## Immediate next action

1. Local Luna xhigh runs exactly one full-panel performance equivalence benchmark
   from `coordination/handoffs/IDX-RUNTIME-PERF-EQUIVALENCE-RUN.md`.
2. If and only if it passes, switch to the Ranking-V2 branch and materialize one
   immutable prepared model cache according to
   `coordination/handoffs/IDX-RANKING-V2-PREPARED-CACHE-RUNTIME.md`.
3. Stop for ChatGPT review of the equivalence report and prepared-cache SHA.
4. Only after that review deploy parallel Luna xhigh candidate workers.

Do **not** deploy the candidate orchestra before the cache is frozen.

## Authorization boundary

Do not:

- rerun Stage 5;
- tune/rescue Ranking V1 against consumed outcomes;
- modify V2 candidate definitions after outcomes start;
- call history through `2026-07-31` independent V2 validation;
- resume Probability V1 calibration;
- start Stage 6;
- run `IDX-VAL-002`;
- make execution-PnL claims;
- paper/live trade;
- merge to `main`.

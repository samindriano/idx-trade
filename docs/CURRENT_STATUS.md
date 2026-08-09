# IDX Trade — Current Status

Date: 2026-08-09 (Asia/Jakarta)

This is the short **authoritative first-read status layer**. For full chronology read
`docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest
checkpoint. If an older "current stage" paragraph conflicts with this file,
this file plus the newest dated checkpoint controls the current phase and
authorization boundary.

## Current phase

- active research branch: `research/idx-stage5-postmortem-v1`
- parent branch: `research/idx-stage5-ranking-holdout-v1`
- Ranking V1: **failed benchmark; rejected as a holdout-passed architecture**
- Stage-5 holdout: **consumed for `RANKING_V1_ONLY`; no retry permitted**
- `holdout_outcome_accessed=true`
- Probability V1: **`PROBABILITY_V1_NOT_READY_DEFERRED`**
- Stage-5 bounded post-mortem: **complete and independently interpreted**
- interpretation checkpoint: `docs/checkpoints/2026-08-09_STAGE5_POSTMORTEM_INTERPRETATION.md`
- next authorized work: **finish runtime-performance equivalence/benchmark, freeze bounded Ranking V2 research specification, then implement V2 development research**
- Stage 6: not authorized for Ranking V1
- independent V2 validation: requires fresh forward data strictly after `2026-07-31`
- `IDX-VAL-002`: not started
- merge to `main`: not authorized
- paper/live trading: not authorized

## Data foundation

Strict execution-grade OHLCV:

- 126 sessions: PASS
- 504 sessions: FAIL because historical Open evidence is incomplete
- 1260 sessions: FAIL for the same execution-grade reason

Signal-research HLCV:

- 1260 sessions: **GO**
- window: `2021-04-29 -> 2026-07-31`
- 979 required common stocks
- 981,940 ACTIVE research rows
- H/L/C/Volume coverage: 100%
- nullable Open rows: 446,843; no synthetic Open
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- manifest SHA-256: `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`
- manifest valid=true, 15/15

## Frozen V1 semantics

- signal after session-t close;
- reference = `Close_t`;
- primary H10 first-touch barrier;
- ATR14, SL=1.0 ATR, RR=1.5;
- same-bar ambiguity not guessed;
- primary causal broad-liquid universe;
- chronological development folds with H20 purge/embargo;
- final locked holdout began at session 1009 / `2025-07-15`.

## Stage 3 / 4 / 4B summary

- Stage 3: `STAGE3_REVIEW_PASS_FOR_BOUNDED_STAGE4_RESEARCH`;
- Stage 4: `STAGE4_RANKING_GO_CALIBRATION_BLOCKED`;
- Stage 4B: `STAGE4B_CALIBRATION_STILL_BLOCKED`;
- Probability V1 calibration rescue stopped permanently after two bounded failures.

Development HGB ranking evidence was positive but modest and did not survive the final locked holdout robustly.

## Stage 5 — final ranking holdout

Automatic result: **`STAGE5_RANKING_HOLDOUT_FAIL`**.

Primary H10:

- 71,420 resolved rows;
- base/prevalence: 0.4071688603;
- HGB PR-AUC: 0.4073793720, delta only +0.0002105118;
- HGB ROC-AUC: 0.4948433255;
- overall Q5-Q1: +0.0108405246;
- top-decile lift: +0.0251666343.

Temporal split:

- HOLDOUT_A: PR-AUC delta vs base +0.0218916273; ROC-AUC 0.5186811460; Q5-Q1 +0.0464755652;
- HOLDOUT_B: PR-AUC delta vs base -0.0105808218; ROC-AUC 0.4810497816; Q5-Q1 -0.0198933303.

Ranking V1 remains a failed benchmark. H5/H20 are near-null sensitivities and cannot rescue V1. The consumed holdout cannot be reused as independent evidence.

## Stage-5 post-mortem — complete

Runtime status: **`DESCRIPTIVE_DIAGNOSTIC_COMPLETE`**.

Read:

- `docs/checkpoints/2026-08-09_STAGE5_POSTMORTEM_RUNTIME.md`;
- `docs/checkpoints/2026-08-09_STAGE5_POSTMORTEM_INTERPRETATION.md`.

Key descriptive findings:

- largest A/B market-state shift: median ATR/Close SMD `+2.2328`;
- breadth return-20 positive SMD `-1.0093`;
- median return-20 SMD `-1.0206`;
- B1 was near-null but B2/B3 turned negative, so lower prevalence alone does not explain failure;
- several core structure feature relationships retained their direction across A/B (`close_position_20`, high/low distance features);
- `atr14_over_close` shifted materially and lost its positive A relationship in B;
- top-decile enrichment appeared in A and disappeared in B, so there is no top-tail rescue of V1;
- `observed_session_count` and `security_age_sessions_exact` drift mechanically with time and must be explicitly controlled/tested in V2 rather than silently relied upon.

Independent interpretation:

**The evidence supports a regime/covariate-shift failure hypothesis for V1 more than a hypothesis that all technical structure information disappeared.** This is a V2 design hypothesis, not a validated causal claim.

## Ranking V2 design direction

Authorized bounded hypotheses for the next specification:

1. within-date cross-sectional / robust normalization of stock features;
2. causal continuous market-state context (breadth, market returns, market volatility, close-position, relative volume/value);
3. market-relative and, if PIT-safe mapping is available, sector-relative strength;
4. explicit control/sensitivity treatment for time/age proxy features;
5. one bounded date-grouped ranking-native challenger versus V1-style binary classifiers;
6. top-tail diagnostics may be reported but no cutoff may be optimized on the consumed holdout.

Because these hypotheses are informed by Stage-5 outcomes, the historical window through `2026-07-31` is now development/research knowledge for Ranking V2. No result on that window is independent final V2 validation.

## Runtime performance track

Separate branch: `perf/idx-research-runtime-v1` / draft PR #9.

Candidate vectorized label engine exists and unit/adversarial equivalence tests pass, but legacy remains authoritative until:

1. exact full frozen-panel legacy-vs-fast equivalence passes;
2. local wall-clock and peak-memory benchmark is recorded under the frozen numerical environment;
3. deterministic feature/label artifacts are cached and hashed so repeated model trials do not rebuild them.

This track may change computation only, never research semantics.

## Authorization boundary

Allowed next work:

1. finish the performance/equivalence track;
2. freeze a bounded Ranking V2 research specification;
3. only then implement V2 development experiments.

Do not:

- rerun Stage 5;
- rescue/tune Ranking V1 against consumed outcomes;
- call the consumed holdout independent V2 validation;
- start Stage 6 for Ranking V1;
- resume Probability V1 calibration rescue;
- run `IDX-VAL-002`;
- make execution-PnL claims;
- paper/live trade;
- merge to `main`.

Any independent Ranking V2 and Probability V2 claim requires **fresh forward evaluation data strictly after `2026-07-31`** after the relevant V2 design/model is frozen.

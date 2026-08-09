# Ranking V3 Research Backlog

Date: 2026-08-10 (Asia/Jakarta)
Status: **IDEA BACKLOG ONLY — NOT AUTHORIZATION TO RUN V3 OUTCOMES**

## Purpose

Record the next-generation Ranking V3 hypotheses identified after Ranking V2 selected and froze `HGB_XS_MARKET` as the historical-development champion.

This file exists so future model work does not depend on chat history. It must be read together with `docs/CURRENT_STATUS.md`, the newest controlling checkpoint/specification, and `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` before any V3 specification or implementation begins.

V2 remains a separate frozen forward-validation track. Nothing in this backlog authorizes reading the reserved V2 fresh-forward outcomes, changing the V2 champion, or modifying the V2 forward contract.

## Research separation / async rule

V3 R&D may proceed asynchronously while V2 accumulates its reserved 100-mature-session fresh-forward block, provided V3 uses only already-authorized development knowledge and does **not** inspect or react to reserved V2 forward outcomes.

If the V2 one-shot forward block is later opened and its result is used to alter V3, that block becomes development knowledge for V3. Any V3 architecture finalized after learning from that result requires a newer independent forward block.

## Current diagnosis motivating V3

V2 evidence suggests that market context improved historical-development robustness, but transportability risk remains:

- `HGB_XS_MARKET` won the frozen V2 selection;
- median PR-AUC delta was positive and Q5-Q1 was positive across all six folds;
- however the latest V2 fold had ROC-AUC below 0.5 despite positive PR-delta/Q5-Q1;
- the V1→V2 post-mortem already showed material volatility, breadth, and market-return regime/covariate shift.

Therefore V3 should primarily test non-stationarity/conditional structure rather than merely perform broad model/hyperparameter search.

## Proposed V3 hypothesis ladder

### V3-Control — frozen V2 champion

Reference comparator: exact `HGB_XS_MARKET` architecture and 25-feature representation.

Purpose: every V3 experiment must prove incremental robustness against the actual V2 champion, not against a weaker baseline.

### Priority 1 — V3-RECENCY

Hypothesis: older observations receive too much influence when market structure drifts over time; recent development observations may deserve greater training weight.

Preferred first experiment because it changes one research dimension while retaining:

- same H10 label;
- same causal universe;
- same 25 V2 features;
- same HGB architecture/hyperparameters;
- same ranking metrics.

Candidate forms should be predeclared before outcome runs. A bounded example for specification work is:

- control: uniform sample weight;
- recency candidate with a moderate exponential half-life, e.g. ~500 official sessions;
- recency candidate with a stronger half-life, e.g. ~250 official sessions.

These numbers are backlog ideas only, not frozen parameters. Do not grid-search many decay values after seeing outcomes.

Primary question: does recency weighting improve q25/worst-fold PR-delta, latest-fold behavior, ROC stability, and Q5-Q1 stability rather than merely the best fold?

Kill quickly if robustness does not improve.

### Priority 2 — V3-REGIME / gated experts

Hypothesis: one global mapping from stock/market features to ranking utility is insufficient across materially different market regimes.

Candidate concept:

- predeclared causal market-state gate using volatility/breadth/market-return context;
- a small bounded set of expert models or conditional models;
- no regime thresholds optimized on reserved V2 forward outcomes.

This is higher-complexity and higher-overfit-risk than V3-RECENCY, so it should follow the cleaner recency test.

Primary question: can explicit conditional specialization improve worst-regime and worst-fold ranking robustness without sacrificing broad coverage?

### Priority 3 — V3-SECTOR-RELATIVE

Hypothesis: stock strength/weakness relative to its own sector contains incremental information beyond whole-market cross-sectional ranks and stock-minus-market context.

Prerequisite: a point-in-time-safe historical sector mapping with explicit effective dates and revision/provenance controls.

Do not backfill today's sector classification over historical rows.

Possible future feature families after PIT mapping is proven:

- within-sector percentile ranks;
- stock-minus-sector-median features;
- sector-relative momentum/volatility/volume;
- sector-state versus market-state context.

### Priority 4 — V3-TRUE-RANKING

Hypothesis: the target task is same-date ranking and a nonlinear learning-to-rank objective may outperform pooled binary HGB while preserving causal/date grouping.

V2 `PAIRWISE_LOGISTIC_XS` tested only a linear pairwise objective and did not establish that nonlinear learning-to-rank is unhelpful.

Possible future research: a tightly bounded LambdaMART/tree-ranking candidate with signal date as the query group, predeclared parameters, and the same chronological validation discipline.

Do not launch a broad ranking-library/hyperparameter tournament.

## What not to do

Do not define V3 as a large indiscriminate model zoo (XGBoost/CatBoost/neural nets/etc.) simply because V2 is frozen. Any candidate must correspond to a specific falsifiable hypothesis.

Do not:

- inspect the reserved V2 forward outcomes during V3 R&D;
- retune V2 and call it V3 without a research hypothesis;
- search many recency half-lives/regime thresholds after seeing fold outcomes;
- use non-PIT sector classifications historically;
- weaken chronological purge/maturity controls;
- optimize solely for average metric while ignoring q25/worst-fold/stability;
- conflate engineering/runtime optimization with model improvement.

## Runtime requirement

Before V3 implementation, read `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`.

Prefer one deterministic Python orchestrator with bounded process/thread scheduling, measured bottleneck profiling, column-projected reads where useful, and semantic-equivalence gates for any optimized path. Do not use many Codex chats as the computational scheduler by default.

## Recommended next V3 specification task

When V3 is separately authorized, the first specification should be a narrow `RANKING_V3_RECENCY_SPEC_V1` containing:

- exact development-data boundary;
- exact control and bounded recency candidates;
- exact sample-weight formula(s) and half-life(s);
- chronological folds/purge/maturity rules;
- primary/secondary metrics;
- robustness eligibility and kill criteria;
- tie-break rules;
- runtime/provenance contract;
- explicit prohibition on V2 reserved-forward outcome access.

Freeze that specification before any V3 recency outcome run.

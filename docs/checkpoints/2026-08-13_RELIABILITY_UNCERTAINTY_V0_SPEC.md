# Reliability / Uncertainty V0 — Frozen Historical Diagnostic

Date: 2026-08-13 (Asia/Jakarta)
Branch: `research/idx-reliability-uncertainty-v0`
Decision: `RELIABILITY_UNCERTAINTY_V0_HISTORICAL_DIAGNOSTIC_AUTHORIZED_FROZEN`

## Research question

Do simple **ex-ante uncertainty diagnostics**, computed without validation outcomes and using only the information available when O2 was scored, robustly stratify historical O2 out-of-fold ranking quality?

V0 is a feasibility diagnostic only. It does **not** train a reliability model, create a composite reliability score, filter trades, change O2 ranking, size positions, or authorize forward deployment.

## Frozen parent

Use the accepted historical O2 development artifacts only:

- O2 branch: `research/idx-ranking-ohlcv-o2-geometry-v1`;
- O2 decision: `O2_SURVIVOR`;
- exact O2 artifact manifest SHA-256: `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`;
- exact O2 OOF predictions SHA-256: `fe02c0c743e7bfc5a57b1c8e731c5685a4bff5f9854f910f88703b15a6ca8f0c`;
- exact common-support key SHA-256: `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- V3-B training table SHA-256: `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe`;
- V3-B final manifest SHA-256: `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9`;
- Open coverage/readiness artifact SHA-256: `d9b2da0b1831b8fe087fe8ee9093e6ce7f649dd0c6c3f6f378cebe23e5694242`;
- O2 feature-order SHA-256: `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`.

Only rows from `fold_predictions.parquet` with `model == O2_OPEN_GEOMETRY` are evaluated. They must retain the exact six O2 folds and historical H10 `binary_target` already emitted by the accepted O2 runtime.

Fresh-forward outcomes, the active O2 forward ledger, forward-outcome markers, O2.1 shadow outcomes, provider calls, and any post-2026-07-31 outcome are prohibited.

## Exact six folds

- V2F1 train 1–504, purge 505–524, validation 525–624;
- V2F2 train 1–624, purge 625–644, validation 645–744;
- V2F3 train 1–744, purge 745–764, validation 765–864;
- V2F4 train 1–864, purge 865–884, validation 885–984;
- V2F5 train 1–984, purge 985–1004, validation 1005–1104;
- V2F6 train 1–1104, purge 1105–1124, validation 1125–1224.

All feature-support statistics for a validation fold are fit from that fold's training rows only.

## Frozen 36-feature information set

Use exact canonical V3-B 33 features followed by:

1. `open_position`;
2. `open_to_high`;
3. `open_to_low`.

Raw missingness is measured **before** any imputation. V0 must not fit a predictive estimator.

## Frozen primary reliability proxies

Higher values always mean **more reliable / less uncertain**.

### P1 — `SCORE_MARGIN_RELIABILITY`

Within each validation signal session, stable-sort by `(O2 score, ticker)`. For each row compute the nearest adjacent score gap; for interior rows use the smaller of the upper/lower gaps, for an edge row use its only adjacent gap. Normalize by that session's score IQR. If IQR is zero/non-finite, the session is ineligible for this proxy.

`score_margin_reliability = nearest_gap / score_iqr`.

Tied scores therefore have zero margin.

### P2 — `JOINT_MARGINAL_SUPPORT_RELIABILITY`

For every feature separately, use only the fold-training observed values to form an empirical CDF. For a validation value `x` define two-sided marginal centrality:

`centrality = 2 * min(F_train(x), 1 - F_train(x))`, clipped to `[1e-6, 1]`.

Missing validation values do not enter this proxy; they are handled by the missingness diagnostic below.

For rows with at least 18 observed features:

`joint_marginal_support_reliability = exp(mean(log(centrality_j)))`.

This is explicitly a deterministic **marginal joint-support proxy**, not a claim of true multivariate nearest-neighbour density.

## Frozen secondary diagnostics — non-gating

- `observed_feature_fraction = observed raw O2 features / 36`;
- `mean_marginal_support = mean(centrality_j)` over observed features.

No additional proxy may be added after seeing V0 outcomes. True multivariate analogue/kNN density is deferred; it is not part of V0.

## Realized historical ranking-quality target

V0 does not create a new trading label. It evaluates whether the ex-ante proxies identify rows where the already-frozen O2 ordering was historically more trustworthy.

For each eligible signal session containing both H10 classes, define row-level `local_pairwise_quality`:

- if `binary_target == 1`: fraction of negative-class peers with lower O2 score, plus half credit for ties;
- if `binary_target == 0`: fraction of positive-class peers with higher O2 score, plus half credit for ties.

The value lies in `[0,1]` and measures each row's local contribution to correct positive-vs-negative ranking. Outcomes are used **only after** all reliability proxies for that fold have been computed.

## Frozen evaluation

A metric-eligible session requires at least 30 O2 validation rows and both H10 classes.

For each primary proxy and each fold persist:

1. median across eligible sessions of Spearman correlation between reliability proxy and `local_pairwise_quality`;
2. mean across eligible sessions of `Q4 - Q1` local-pairwise-quality lift, where reliability quartiles are deterministic equal-count ordinal buckets within session;
3. selective-quality lift at fixed 40% coverage: mean local-pairwise quality among the top 40% reliability rows within each session minus the full-session mean quality;
4. conditional lift after controlling for O2 alpha strength: within each session first split O2 score into deterministic quintiles; within each score quintile with at least 8 rows, compare the upper versus lower half of the reliability proxy, then average those differences for the session.

Persist the same descriptive metrics for the two secondary diagnostics, but they do not determine the V0 verdict.

## Data-readiness gate

`RELIABILITY_V0_DATA_READY` requires all of:

1. all pinned parent/artifact/feature hashes match;
2. candidate O2 OOF rows have unique `(fold,ticker,date,signal_session_index)` keys and finite O2 scores;
3. OOF fold/session indices exactly obey the frozen six validation windows;
4. the exact 36 raw feature values can be reconstructed for every OOF key from the pinned V3-B table plus pinned Open coverage artifact;
5. every fold has at least 80 metric-eligible validation sessions;
6. every fold has usable training observations for every feature required by the support proxy;
7. no post-2026-07-31 outcome, provider call, fresh-forward runtime/outcome marker, or O2 rescore/refit is accessed.

Failure gives `RELIABILITY_V0_DATA_BLOCKED` and stops the lane.

## Frozen feasibility gate

Evaluate P1 and P2 independently. A primary proxy **qualifies** only if all are true across the six folds:

1. median fold `median_session_spearman > 0`;
2. q25 across fold `median_session_spearman > 0`;
3. at least 4/6 folds have positive `median_session_spearman`;
4. median fold `mean_q4_minus_q1_quality_lift > 0` and at least 4/6 folds are positive;
5. median fold `mean_selective_quality_lift_at_40pct > 0` and at least 4/6 folds are positive;
6. median fold `mean_conditional_quality_lift > 0` and at least 4/6 folds are positive.

V0 receives `RELIABILITY_V0_FEASIBILITY_GO` if **either predefined primary proxy** qualifies. Otherwise verdict is `RELIABILITY_V0_NO_SIGNAL`.

Because two primary hypotheses are evaluated, any GO remains historical-development feasibility evidence only. It does not authorize a reliability model or a trade-selection rule; a V1 contract must be frozen separately and reviewed before fitting anything.

## Required artifacts

Persist at minimum:

- `preflight_contract.json`;
- `proxy_rows.parquet` with OOF identity, score, target, four frozen diagnostics and realized local quality;
- `session_metrics.csv`;
- `fold_proxy_metrics.csv`;
- `proxy_gate_summary.csv`;
- `aggregate_decision.json`;
- `artifact_manifest.json` with hashes and runtime flags.

## Minimum tests

Tests must cover:

- score-margin ties and edge rows;
- empirical-support training-only behavior and missingness separation;
- local pairwise quality for both classes and ties;
- deterministic reliability quartiles/top-40% selection;
- conditional-within-O2-score-quintile metric;
- exact fold-window rejection;
- gate boundary behavior;
- protected runtime flags / no fresh-forward access.

## Hard stop

Run this frozen diagnostic once. Do not add a proxy, alter a threshold, combine P1/P2, fit a reliability estimator, optimize trade filters, or inspect fresh-forward outcomes in response to the result. Stop for independent review after the V0 verdict.

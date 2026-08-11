# OHLCV O2 — Frozen Minimality Ablation Specification

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-minimality-v1`
Parent independent-review commit: `0e45168a2f51deed5ec70503919d5832d328cf54`
Decision: `O2_MINIMALITY_ABLATION_AUTHORIZED`

## Purpose

Determine whether the accepted three-feature `O2_OPEN_GEOMETRY` representation can be simplified while preserving its robust historical-development ranking signal.

This is a bounded ablation of already-observed O2 information. It is not authorization to engineer new Open features or tune the model.

## Frozen population and contract

Use exactly the same `278,168` common-support row identities and `729` tickers as O1/O2, with common-support key SHA-256:

`716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`

Reproduce exactly:

- canonical V3-B 33-feature baseline/order/hash;
- H10 label contract;
- six expanding historical-development folds with the frozen 20-session purge and 100-session validation blocks;
- HGB preprocessing and parameters;
- evaluator and ranking metrics;
- accepted O2 geometry values from the same coverage artifact.

No population recomputation or enlargement is allowed.

## Frozen candidate set

Train exactly these eight models on identical rows/folds:

1. `V3B_COMMON_SUPPORT_BASELINE` — canonical 33 V3-B features only.
2. `O2_FULL_3` — baseline + `open_position`, `open_to_high`, `open_to_low`.
3. `O2_SINGLE_POSITION` — baseline + `open_position`.
4. `O2_SINGLE_TO_HIGH` — baseline + `open_to_high`.
5. `O2_SINGLE_TO_LOW` — baseline + `open_to_low`.
6. `O2_PAIR_POSITION_HIGH` — baseline + `open_position`, `open_to_high`.
7. `O2_PAIR_POSITION_LOW` — baseline + `open_position`, `open_to_low`.
8. `O2_PAIR_HIGH_LOW` — baseline + `open_to_high`, `open_to_low`.

No other candidate is allowed.

Rationale: the three accepted O2 columns satisfy an exact algebraic relation, so all one-feature and two-feature representations are the complete bounded minimality set. This run must not create transformations, interactions, normalized variants, ATR variants, ranks, or regime-conditioned features.

## Training protocol

- historical-development data only through 2026-07-31;
- identical train/validation identities for all eight models within each fold;
- exact same HGB preprocessing/parameters and random seed;
- no hyperparameter tuning;
- no early stopping or candidate-specific pipeline change;
- no use of fresh-forward outcomes;
- no provider/network calls.

## Required metrics

For every model/fold report:

- prevalence;
- PR-AUC and PR-AUC minus prevalence;
- paired PR-AUC delta versus `V3B_COMMON_SUPPORT_BASELINE`;
- paired PR-AUC delta versus `O2_FULL_3` for all reduced variants;
- ROC-AUC;
- Q5-Q1;
- top-decile lift;
- train/validation row counts;
- feature order/hash;
- runtime.

Aggregate for every model:

- mean/median PR-AUC;
- median and lower-quartile paired PR-AUC delta versus baseline;
- minimum fold paired delta versus baseline;
- positive-fold count versus baseline;
- mean/median ROC-AUC;
- mean/median Q5-Q1;
- mean top-decile lift.

Also apply the original O2 survivor diagnostics to each reduced representation strictly as diagnostics:

- median paired PR-AUC delta versus baseline > 0;
- lower-quartile paired PR-AUC delta versus baseline > 0;
- uplift not explained by one isolated fold spike;
- no clear aggregate ROC/Q5-Q1 guardrail reversal.

Do not invent a new numeric non-inferiority threshold after seeing results.

## Output decision

The runtime must emit only:

`O2_MINIMALITY_EVIDENCE_COMPLETE`

It must not automatically declare a final O2 representation or champion replacement. Persist the complete ablation evidence and stop for independent ChatGPT review, which will decide whether a single-feature, two-feature, or full-three representation should advance to final-freeze review.

## Protected boundary

Not authorized:

- O3 or any new Open feature;
- feature interactions or regime adaptation;
- HGB tuning;
- post-2026-07-31 fresh-forward outcome access;
- final refit or canonical V3-B replacement;
- Open repair/provider calls;
- execution/PnL, Path Risk, probability/payoff/reliability, paper/live or broker work.

## Required artifacts

Persist a dated runtime checkpoint and immutable external artifacts/hashes covering preflight contract, exact row identities, feature manifests, fold definitions, fold predictions, fold metrics, aggregate metrics, reduced-vs-full paired comparison, survivor diagnostics, and runtime summary. Run focused tests and full pytest, push fast-forward, then STOP for independent ChatGPT review.

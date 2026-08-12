# O2 vs V2 Common-Support Historical Comparator — Frozen Spec

Date: 2026-08-12 (Asia/Jakarta)
Status: `O2_V2_COMMON_SUPPORT_COMPARATOR_AUTHORIZED`
Branch: `research/idx-ranking-o2-v2-common-support-comparator-v1`

## Purpose

Run one bounded direct historical comparison between the frozen Ranking-V2 historical champion `HGB_XS_MARKET` and the selected O2 representation `O2_FULL_3`.

This is historical-development evidence only. It does not alter canonical model status, authorize fresh-forward outcome access, or reopen feature/model search.

## Exact comparison population

Both models must be trained and evaluated on the exact accepted O2 common-support population:

- rows: `278168`
- tickers: `729`
- row identity SHA-256: `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`

No model-specific row filtering, population enlargement, synthetic Open, or recomputation of common support is allowed.

## Models

Exactly two models are authorized.

### V2 comparator

`V2_HGB_XS_MARKET_COMMON_SUPPORT`

- exact frozen 25-feature `HGB_XS_MARKET` feature list/order from Ranking V2;
- obtain and persist the exact feature-order hash from frozen V2 artifacts; do not infer or reorder columns;
- HGB parameters exactly: `learning_rate=0.05`, `max_iter=200`, `max_leaf_nodes=31`, `l2_regularization=1.0`, `random_state=42`;
- same frozen training-only preprocessing semantics as the accepted Ranking-V2 HGB pipeline;
- no Open-derived feature.

### O2 comparator

`O2_FULL_3_COMMON_SUPPORT`

- exact accepted 36-feature order = canonical V3-B 33 features followed by `open_position`, `open_to_high`, `open_to_low`;
- required feature-order SHA-256: `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
- exact accepted O2 preprocessing/HGB parameters and seed;
- no feature change or tuning.

## Labels and folds

Use the exact historical H10 target semantics `TP_FIRST=1`, `SL_FIRST=0` and the same six expanding folds with 20-session purge and 100-session validation:

- V2F1 train 1-504, purge 505-524, validation 525-624
- V2F2 train 1-624, purge 625-644, validation 645-744
- V2F3 train 1-744, purge 745-764, validation 765-864
- V2F4 train 1-864, purge 865-884, validation 885-984
- V2F5 train 1-984, purge 985-1004, validation 1005-1104
- V2F6 train 1-1104, purge 1105-1124, validation 1125-1224

Both models must see identical training and validation row identities within each fold.

## Required metrics

Persist per-fold and aggregate metrics for both models:

- prevalence
- PR-AUC
- PR-AUC minus prevalence
- ROC-AUC
- Q5-Q1
- top-decile lift

Persist paired `O2 - V2` deltas per fold for PR-AUC, ROC-AUC, Q5-Q1, and top-decile lift.

## Frozen comparator verdict

Primary metric is paired PR-AUC delta (`O2 - V2`).

Emit `O2_DIRECT_V2_COMMON_SUPPORT_BETTER` only if all are true:

1. median paired PR-AUC delta > 0;
2. lower-quartile paired PR-AUC delta > 0;
3. paired PR-AUC delta > 0 in at least 4/6 folds;
4. no aggregate ranking guardrail reversal, defined as both median ROC-AUC and median Q5-Q1 being worse for O2 than V2.

Otherwise emit `O2_DIRECT_V2_COMMON_SUPPORT_NOT_ESTABLISHED`.

This verdict is descriptive historical-development evidence and cannot promote or demote any canonical/fresh-forward model by itself.

## Reproducibility and safety

Before fitting:

- verify exact common-support row hash;
- verify frozen V2 artifacts and exact 25-feature identity/order;
- verify accepted O2 parent artifacts and 36-feature hash;
- verify frozen H10/fold contracts;
- run focused preflight tests.

Persist predictions, fold metrics, aggregate metrics, paired comparison, input/hash manifest, environment manifest, and artifact manifest with SHA-256 values.

Forbidden:

- fresh-forward outcome access;
- provider/network calls;
- O2 or V2 final-model overwrite;
- tuning/calibration;
- additional models or features;
- population repair/enlargement;
- forward scoring/counter changes.

Run focused and full pytest after implementation/runtime. Push the runtime checkpoint and STOP for independent ChatGPT review.
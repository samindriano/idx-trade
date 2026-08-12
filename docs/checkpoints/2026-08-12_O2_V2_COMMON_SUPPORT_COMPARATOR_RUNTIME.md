# O2 vs V2 Common-Support Comparator Runtime

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-o2-v2-common-support-comparator-v1`
Starting remote HEAD: `f3297c19adbb8e890b56849daa895aee36fe1fc6`
Runtime status: `O2_DIRECT_V2_COMMON_SUPPORT_BETTER`

## Scope and boundary

This run executed only the frozen historical O2-vs-V2 common-support
comparator. It trained exactly two models, made no provider/network calls,
accessed no fresh-forward outcomes, did not tune or add features, and did not
overwrite either canonical model.

The runtime artifact root is external to Git:

`D:\Documents\Project\idx-trade-data-gate-20260808v\o2_v2_common_support_comparator_v1_20260812_retry1`

The first attempted runtime stopped before final metrics because the shared
aggregate schema did not include median top-decile lift. The smallest derived
median column was added, and the successful retry used a new external root;
the incomplete first root was preserved and not treated as a result.

## Frozen inputs

- common-support rows: `278,168`;
- common-support tickers: `729`;
- common-support row identity SHA-256:
  `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- canonical V3-B 33-feature order SHA-256:
  `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- V2 25-feature order SHA-256:
  `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72`;
- O2 36-feature order SHA-256:
  `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
- H10 labels: `TP_FIRST=1`, `SL_FIRST=0`;
- folds: exact `V2F1`--`V2F6`, expanding train, H20 purge, 100-session
  validation;
- HGB parameters: learning rate `0.05`, `max_iter=200`,
  `max_leaf_nodes=31`, `l2_regularization=1.0`, `random_state=42`;
- preprocessing: median imputation with indicators and
  `keep_empty_features=True`, selected columns in frozen order, remainder
  dropped;
- immutable panel SHA-256 before and after:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- V2 candidate summary SHA-256:
  `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- V2 final manifest SHA-256:
  `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9`;
- V2 final model SHA-256:
  `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace`;
- V2 prepared-cache manifest SHA-256:
  `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- V2 prepared-cache SHA-256:
  `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`.

## Models

1. `V2_HGB_XS_MARKET_COMMON_SUPPORT`: exact frozen V2 25-feature order.
2. `O2_FULL_3_COMMON_SUPPORT`: canonical V3-B 33 features followed by
   `open_position`, `open_to_high`, `open_to_low`.

For every fold, both models used the same train and validation row identities.
`fold_row_identity_checks.csv` records the six shared train/validation hashes;
all six `identical_train_validation_identities` values are `True`.

## Per-fold metrics

Values below are rounded to six decimals for readability. The complete
unrounded metrics and all paired deltas are in `fold_metrics.csv` and
`paired_comparisons.csv`.

| fold | prevalence | V2 PR-AUC | O2 PR-AUC | delta PR-AUC | V2 PR-prev | O2 PR-prev | V2 ROC-AUC | O2 ROC-AUC | delta ROC | V2 Q5-Q1 | O2 Q5-Q1 | delta Q5-Q1 | V2 top-decile lift | O2 top-decile lift | delta top-decile |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V2F1 | 0.380122 | 0.408797 | 0.415518 | +0.006722 | 0.028675 | 0.035396 | 0.533371 | 0.537553 | +0.004183 | 0.061385 | 0.089033 | +0.027649 | 0.039204 | 0.056979 | +0.017776 |
| V2F2 | 0.387545 | 0.414081 | 0.411250 | -0.002832 | 0.026536 | 0.023704 | 0.530136 | 0.529555 | -0.000581 | 0.060684 | 0.093839 | +0.033155 | 0.040677 | 0.054837 | +0.014160 |
| V2F3 | 0.414118 | 0.423513 | 0.426907 | +0.003394 | 0.009395 | 0.012789 | 0.529719 | 0.535664 | +0.005945 | 0.034985 | 0.056654 | +0.021669 | 0.020455 | 0.039286 | +0.018831 |
| V2F4 | 0.384608 | 0.433632 | 0.435877 | +0.002244 | 0.049025 | 0.051269 | 0.516955 | 0.527712 | +0.010756 | 0.058877 | 0.042160 | -0.016718 | 0.013648 | 0.020915 | +0.007267 |
| V2F5 | 0.462106 | 0.490434 | 0.501605 | +0.011171 | 0.028328 | 0.039499 | 0.531260 | 0.540882 | +0.009622 | 0.040765 | 0.081196 | +0.040431 | 0.033823 | 0.066006 | +0.032183 |
| V2F6 | 0.336487 | 0.347770 | 0.350254 | +0.002484 | 0.011283 | 0.013767 | 0.491318 | 0.496630 | +0.005312 | 0.039794 | 0.041916 | +0.002123 | 0.016245 | 0.015057 | -0.001188 |

## Aggregate evidence

| model | mean PR-AUC | median PR-AUC | mean PR-AUC-prev | median PR-AUC-prev | mean ROC-AUC | median ROC-AUC | mean Q5-Q1 | median Q5-Q1 | mean top-decile lift | median top-decile lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V2_HGB_XS_MARKET_COMMON_SUPPORT | 0.419704 | 0.418797 | 0.025540 | 0.027432 | 0.522126 | 0.529927 | 0.049415 | 0.049821 | 0.027342 | 0.027139 |
| O2_FULL_3_COMMON_SUPPORT | 0.423568 | 0.421213 | 0.029404 | 0.029550 | 0.527999 | 0.532609 | 0.067467 | 0.068925 | 0.042180 | 0.047062 |

Paired O2 minus V2 aggregate means are PR-AUC `+0.003864`, ROC-AUC
`+0.005873`, Q5-Q1 `+0.018052`, and top-decile lift `+0.014838`.

## Frozen verdict

The exact comparator rule produced:

- median paired PR-AUC delta: `+0.002939019431462575`;
- lower-quartile paired PR-AUC delta: `+0.002304097591101159`;
- positive paired PR-AUC folds: `5/6`;
- median ROC-AUC guardrail reversal: `false`;
- verdict: `O2_DIRECT_V2_COMMON_SUPPORT_BETTER`.

This is historical-development evidence only. It does not authorize forward
scoring, a final refit, canonical model replacement, or execution use.

## Validation and artifacts

- focused frozen-model tests: `12 passed`;
- scoped full pytest: `293 passed, 5 warnings`;
- provider/network calls: none;
- fresh-forward outcomes accessed: `false`;
- artifact manifest SHA-256:
  `e853599babef5ef51cd484ddaf2c3d83b3a2f3f9be40d43beb5361955b9cf7cf`;
- artifact files listed: `10`;
- all `10/10` artifact hashes re-verified after runtime.

## Stop condition

Stop for independent ChatGPT review. No forward scoring, new model, provider
call, canonical overwrite, or downstream experiment was started.

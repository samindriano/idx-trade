# Stage 5 Post-Mortem Runtime

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage5-postmortem-v1`
Substantive diagnostic code commit: `f51f9778a6657b52752d2423dbde8499c693bf70`

## Status and scope

Runtime status: **`DESCRIPTIVE_DIAGNOSTIC_COMPLETE`**.

This was exactly one bounded descriptive post-mortem of the already-failed
Stage-5 Ranking V1 holdout. It did not retrain, tune, select features, search
thresholds, fit calibration, alter labels, rerun Stage 5, or implement V2.
The consumed holdout remains diagnostic data only and cannot regain independent
validation status.

Probability V1 remains **`PROBABILITY_V1_NOT_READY_DEFERRED`**. No Stage 6,
Probability V2, `IDX-VAL-002`, execution-PnL claim, paper/live trading, or
main merge was started.

## Environment and validation

- Python 3.13.5
- NumPy 2.4.2
- pandas 2.3.3
- pyarrow 23.0.1
- scikit-learn 1.8.0

Full pytest: **211 passed, 0 failed**, with three existing pandas
FutureWarnings.

The branch was clean at HEAD
`151e2f74507031077481f9a3131b9f85a0c145e8`. No `src/` or `tests/` changes
were present after the substantive diagnostic commit.

## Exact inputs

| input | SHA-256 |
|---|---|
| signal panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| Stage-5 predictions | `9d850776c98c07e069b32d606ad510d94a26435659da86997f5302d765d8ee8c` |
| Stage-5 summary | `1a38171eead5a9c72de62da4f6ef486f35e3fba2e962c3b0bccac9fea033acd0` |

The Stage-5 summary guards were `decision=STAGE5_RANKING_HOLDOUT_FAIL`,
`holdout_consumed=true`, `holdout_consumed_for=RANKING_V1_ONLY`, and
`holdout_outcome_accessed=true`. The durable global marker existed and agreed.

## Fixed temporal blocks

The HGB score and six block boundaries were frozen before runtime:

| block | sessions | rows | prevalence | PR-AUC | ROC-AUC | PR-AUC - prevalence | Q5-Q1 | top-decile rate | top-decile lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | 1009-1048 | 8,969 | 0.4552346973 | 0.4873990264 | 0.5205789227 | 0.0321643291 | 0.0436252789 | 0.5301866081 | 0.0749519108 |
| A2 | 1049-1088 | 10,915 | 0.4490151168 | 0.4506310580 | 0.5002196297 | 0.0016159412 | -0.0076857955 | 0.4676258993 | 0.0186107825 |
| A3 | 1089-1129 | 13,119 | 0.4843356963 | 0.5148689370 | 0.5313986615 | 0.0305332407 | 0.0936463819 | 0.5583145222 | 0.0739788259 |
| B1 | 1130-1169 | 14,395 | 0.2765543592 | 0.2779488969 | 0.5066507094 | 0.0013945378 | -0.0261259582 | 0.2829670330 | 0.0064126738 |
| B2 | 1170-1209 | 13,203 | 0.3996061501 | 0.3866717419 | 0.4724630688 | -0.0129344083 | -0.0343101852 | 0.3808812547 | -0.0187248954 |
| B3 | 1210-1250 | 10,819 | 0.4145484795 | 0.4068083572 | 0.4848301305 | -0.0077401223 | 0.0056943535 | 0.4237749546 | 0.0092264751 |

The fixed-block result is descriptive. It does not create new validation folds
or authorize a new cutoff.

## Feature distribution drift

The 12 frozen baseline features were compared using finite rows, missingness,
mean, median, standard deviation, standardized mean difference, and median
shift over pooled IQR. Sorted by absolute SMD:

| feature | A mean | B mean | A median | B median | A missing | B missing | SMD B-A | median shift / pooled IQR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| atr14_over_close | 0.051278 | 0.072233 | 0.043290 | 0.063860 | 0.000000 | 0.000000 | 0.558396 | 0.435700 |
| security_age_sessions_exact | 552.755 | 706.267 | 556.000 | 714.000 | 0.688028 | 0.671994 | 0.553792 | 0.389163 |
| distance_low_60_atr | 4.423340 | 3.017997 | 3.878378 | 2.560976 | 0.010272 | 0.002811 | -0.493569 | -0.401619 |
| observed_session_count | 893.213 | 1004.177 | 1036.000 | 1145.000 | 0.000000 | 0.000000 | 0.390157 | 0.331307 |
| close_return_20 | 0.085046 | -0.024439 | 0.009091 | -0.042467 | 0.000182 | 0.000026 | -0.227656 | -0.291414 |
| close_position_20 | 0.463856 | 0.402998 | 0.448980 | 0.363636 | 0.000000 | 0.000000 | -0.220404 | -0.185216 |
| log_regular_value_relative_20 | 0.083588 | -0.057994 | -0.002897 | -0.090864 | 0.000000 | 0.000000 | -0.164753 | -0.097966 |
| distance_low_20_atr | 2.248809 | 2.014877 | 1.872611 | 1.707317 | 0.000000 | 0.000000 | -0.143081 | -0.080578 |
| close_return_5 | 0.024909 | -0.009725 | 0.000000 | -0.011111 | 0.000000 | 0.000000 | -0.108276 | -0.133976 |
| distance_high_20_atr | 2.828484 | 3.194466 | 2.255034 | 2.893855 | 0.000000 | 0.000000 | 0.045302 | 0.260123 |
| relative_volume_20 | 1.674585 | 1.579640 | 0.991024 | 0.941205 | 0.000000 | 0.000000 | -0.020578 | -0.057978 |
| distance_high_60_atr | 7.101129 | 7.775152 | 4.127328 | 6.240963 | 0.010272 | 0.002811 | 0.028303 | 0.354258 |

The largest absolute shifts were `atr14_over_close`,
`security_age_sessions_exact`, `distance_low_60_atr`,
`observed_session_count`, and `close_return_20`. These are distributional
observations, not evidence that any feature should be selected or removed.

## Feature/outcome relationship drift

The table reports within-date percentile-rank correlation with the binary
target and feature Q5-Q1 target-rate spread for each half. All 12 frozen
features are retained; no feature selection was performed.

| feature | A rank corr | A Q5-Q1 | B rank corr | B Q5-Q1 |
|---|---:|---:|---:|---:|
| close_return_5 | -0.006753 | -0.004215 | -0.020119 | -0.029407 |
| close_return_20 | -0.012293 | -0.006448 | -0.040785 | -0.050373 |
| atr14_over_close | 0.031020 | 0.045160 | 0.000047 | -0.006412 |
| close_position_20 | -0.032992 | -0.043937 | -0.040486 | -0.042126 |
| distance_high_20_atr | 0.019108 | 0.023716 | 0.033252 | 0.036631 |
| distance_low_20_atr | -0.040435 | -0.051292 | -0.041051 | -0.051239 |
| distance_high_60_atr | 0.019424 | 0.026028 | 0.030461 | 0.043919 |
| distance_low_60_atr | -0.040327 | -0.051278 | -0.040706 | -0.054769 |
| relative_volume_20 | -0.019079 | -0.032408 | 0.004683 | 0.004715 |
| log_regular_value_relative_20 | -0.017527 | -0.026314 | 0.002390 | 0.002271 |
| observed_session_count | -0.015237 | -0.014455 | 0.002366 | 0.005933 |
| security_age_sessions_exact | 0.019825 | 0.019516 | 0.007598 | -0.012911 |

Factual Q5-Q1 sign reversals from A to B were:

- `atr14_over_close`: positive to negative;
- `log_regular_value_relative_20`: negative to positive;
- `observed_session_count`: negative to positive;
- `relative_volume_20`: negative to positive;
- `security_age_sessions_exact`: positive to negative.

These reversals are descriptive and are not independently validated predictive
claims.

## Market/regime drift

Daily summaries use the full causal primary-liquid universe by date, not only
rows with resolved holdout labels.

| metric | A mean | B mean | A median | B median | SMD B-A |
|---|---:|---:|---:|---:|---:|
| primary-liquid universe size | 332.306 | 375.174 | 348.000 | 376.000 | 0.871489 |
| breadth return 5 positive | 0.471207 | 0.406786 | 0.455470 | 0.400498 | -0.329467 |
| breadth return 20 positive | 0.534641 | 0.355068 | 0.520725 | 0.280660 | -1.009255 |
| median return 5 | 0.000100 | -0.016921 | 0.000000 | -0.008885 | -0.451839 |
| median return 20 | 0.011008 | -0.056639 | 0.007375 | -0.065657 | -1.020589 |
| median ATR/Close | 0.045159 | 0.067881 | 0.045040 | 0.065270 | 2.232811 |
| median close position 20 | 0.444523 | 0.368600 | 0.432314 | 0.380000 | -0.549442 |
| median relative volume 20 | 0.981188 | 0.910382 | 0.973407 | 0.891084 | -0.377209 |
| median relative regular-market value | -0.022366 | -0.162251 | -0.025812 | -0.166943 | -0.643386 |

No regime threshold was optimized. The descriptive A/B environment differs in
breadth, returns, volatility, close position, relative volume, and relative
market value.

## HGB decile curves

Within-date HGB deciles were reported separately; no new cutoff was selected.

| half | decile 1 | decile 2 | decile 3 | decile 4 | decile 5 | decile 6 | decile 7 | decile 8 | decile 9 | decile 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HOLDOUT_A TP rate | 0.449722 | 0.449955 | 0.438202 | 0.447233 | 0.464738 | 0.458169 | 0.476494 | 0.469573 | 0.471641 | 0.520585 |
| HOLDOUT_B TP rate | 0.370546 | 0.368339 | 0.346375 | 0.357255 | 0.358364 | 0.351281 | 0.369231 | 0.356827 | 0.342545 | 0.356428 |
| HOLDOUT_A lift | -0.015023 | -0.014791 | -0.026543 | -0.017512 | -0.000008 | -0.006577 | 0.011748 | 0.004827 | 0.006895 | 0.055839 |
| HOLDOUT_B lift | 0.012840 | 0.010633 | -0.011332 | -0.000452 | 0.000657 | -0.006426 | 0.011525 | -0.000880 | -0.015162 | -0.001278 |

The top decile was enriched in A but not in B. This is a descriptive result,
not a validated top-decile strategy.

## External output artifacts

Output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\stage5_postmortem_v1_20260809`

| artifact | SHA-256 |
|---|---|
| `postmortem_fixed_block_metrics.csv` | `fc4a951814c7021c4de3a914b7fc435186c312cea64ab61c728ba9d6ae1a036c` |
| `postmortem_feature_drift_a_vs_b.csv` | `9ac23cba81ed9043d833eddc7e425db5574831d7fcde464fac945fd49fa4da84` |
| `postmortem_feature_target_relation_by_half.csv` | `4956dc222f8aa41f85141681cd7efdc184a29ac9c99bcc184ce36548afaf5454` |
| `postmortem_market_regime_daily.csv` | `cb652271ad952cedfe9cc343a08238d13eb9a6a880e6f25eb963065459312b47` |
| `postmortem_market_regime_a_vs_b.csv` | `25dde20247b61b80afa3840553f4bc7cb79962daed99d36ddfe746e3f294c116` |
| `postmortem_hgb_deciles_by_half.csv` | `e9b9c9665f2480bcad5143febc2e6e1d98dc37edc65364381f05d7750175c7af` |
| `postmortem_summary.json` | `9f6c60ea3602673ad500adc99def8b1ecdfb7006c47c750dd52b2cf89984cad1` |

The summary interpretation policy is
`DIAGNOSTIC_OR_V2_HYPOTHESIS_ONLY_NOT_VALIDATED_CLAIM`, and its future
validation policy is fresh forward data strictly after `2026-07-31`.

## Stop boundary

Ranking V1 remains a failed benchmark and the holdout remains consumed for
`RANKING_V1_ONLY`. No V2 was implemented, no Stage 6 or `IDX-VAL-002` was
started, no paper/live trading occurred, and no main merge occurred. Stop for
independent ChatGPT interpretation.

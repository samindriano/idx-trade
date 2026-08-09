# Stage-4 V1 Development Runtime

Date: 2026-08-09 (Asia/Jakarta)

Branch: `research/idx-stage4-v1`

Code head used by the runner: `ad2098c7932a187555ac7c9ec8b77372bdf622e5`

Automatic status: **STAGE4_RANKING_GO_CALIBRATION_BLOCKED**

This was an execution-only run of the already-frozen Stage-4 V1 runtime. No
research/model pipeline redesign, tuning, external data, market redownload,
Open synthesis, execution-PnL, sizing, holdout inspection, Stage 5,
`IDX-VAL-002`, or main merge was performed.

## Admission and safety

- Python: `3.13.5`
- NumPy: `2.4.2`
- pandas: `2.3.3`
- pyarrow: `23.0.1`
- scikit-learn: `1.8.0`
- seed: `42`
- full pytest: **192 passed, 0 failed**; three existing pandas/NumPy
  `FutureWarning` messages
- `holdout_outcome_accessed=false`
- locked holdout start: index `1009`, date `2025-07-15`
- Stage-3 maximum signal read: index `942`, date `2025-03-20`
- Stage-3 maximum future source read: index `962`, date `2025-04-29`

Exact Stage-3 input hashes:

| input | SHA-256 |
|---|---|
| primary model table | `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189` |
| development feature table | `f16d77caa6642d0aba8c0a39eda5b2d32e53f17717b149f5f0637eeacac80772` |
| Stage-3 runtime summary | `979c56be43e2fdc5c0502e1b1625d74dbcab6ba28f097338575479739baa029f` |
| exact official 1,260-session calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |

The calendar window was exactly `2021-04-29` through `2026-07-31`, with 1,260
official sessions.

## Stage-3 reference reproduction

Metrics are development-fold diagnostics. `gap` is the absolute prevalence
gap.

| fold | model | rows | positive | PR-AUC | ROC-AUC | Brier | ECE | gap |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| F1 | base_rate | 28,380 | 0.387562 | 0.387562 | 0.500000 | 0.237358 | 0.000578 | 0.000578 |
| F1 | momentum_20 | 28,380 | 0.387562 | 0.399449 | 0.513291 | 0.237324 | 0.010380 | 0.007291 |
| F1 | logistic_compact | 28,380 | 0.387562 | 0.396229 | 0.509533 | 0.237952 | 0.025975 | 0.023301 |
| F1 | hist_gradient_boosting | 28,380 | 0.387562 | 0.413738 | 0.515887 | 0.237056 | 0.017066 | 0.009158 |
| F2 | base_rate | 25,807 | 0.413996 | 0.413996 | 0.500000 | 0.243261 | 0.025642 | 0.025642 |
| F2 | momentum_20 | 25,807 | 0.413996 | 0.409829 | 0.492574 | 0.243450 | 0.027517 | 0.025583 |
| F2 | logistic_compact | 25,807 | 0.413996 | 0.416872 | 0.503967 | 0.243840 | 0.035050 | 0.034205 |
| F2 | hist_gradient_boosting | 25,807 | 0.413996 | 0.425449 | 0.502705 | 0.243212 | 0.026906 | 0.025581 |
| F3 | base_rate | 27,178 | 0.325300 | 0.325300 | 0.500000 | 0.223781 | 0.065584 | 0.065584 |
| F3 | momentum_20 | 27,178 | 0.325300 | 0.328895 | 0.490886 | 0.227243 | 0.087001 | 0.085073 |
| F3 | logistic_compact | 27,178 | 0.325300 | 0.350202 | 0.523421 | 0.225378 | 0.078397 | 0.078397 |
| F3 | hist_gradient_boosting | 27,178 | 0.325300 | 0.364907 | 0.538533 | 0.225813 | 0.083919 | 0.083919 |

HGB beat both base-rate and momentum PR-AUC in `F1`, `F2`, and `F3`; the
Stage-3 advancement rule reproduced as `true`.

Pooled reference OOF metrics:

| model | rows | positive | mean probability | PR-AUC | ROC-AUC | Brier | weighted ECE | gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| base_rate | 81,365 | 0.375149 | 0.388721 | 0.358384 | 0.470722 | 0.234695 | 0.030241 | 0.013572 |
| momentum_20 | 81,365 | 0.375149 | 0.392908 | 0.353278 | 0.470566 | 0.235900 | 0.041409 | 0.017759 |
| logistic_compact | 81,365 | 0.375149 | 0.382359 | 0.364646 | 0.478358 | 0.235620 | 0.046363 | 0.007210 |
| hist_gradient_boosting | 81,365 | 0.375149 | 0.391872 | 0.374347 | 0.485964 | 0.235253 | 0.042517 | 0.016723 |

## Frozen feature-family ablation

Values in each metric column are `F1 / F2 / F3`. Delta is removal minus
`HGB_FULL` mean PR-AUC.

| variant | PR-AUC | mean delta | ROC-AUC | Brier | ECE |
|---|---|---:|---|---|---|
| HGB_FULL | 0.413738 / 0.425449 / 0.364907 | 0.000000 | 0.515887 / 0.502705 / 0.538533 | 0.237056 / 0.243212 / 0.225813 | 0.017066 / 0.026906 / 0.083919 |
| HGB_NO_STRUCTURE | 0.404953 / 0.414291 / 0.345831 | -0.013006 | 0.517526 / 0.499280 / 0.527392 | 0.237197 / 0.243332 / 0.226362 | 0.012063 / 0.025770 / 0.084160 |
| HGB_NO_MOMENTUM | 0.406516 / 0.419222 / 0.354712 | -0.007881 | 0.517633 / 0.497237 / 0.534223 | 0.237218 / 0.243274 / 0.226130 | 0.011462 / 0.026219 / 0.084430 |
| HGB_NO_VOLUME_LIQUIDITY | 0.412913 / 0.428446 / 0.360047 | -0.000896 | 0.518144 / 0.504200 / 0.536693 | 0.237065 / 0.243198 / 0.225827 | 0.010528 / 0.025720 / 0.083919 |
| HGB_NO_VOLATILITY | 0.415445 / 0.423671 / 0.359344 | -0.001878 | 0.514930 / 0.498896 / 0.530642 | 0.237063 / 0.243217 / 0.225821 | 0.015335 / 0.026099 / 0.084299 |
| HGB_NO_HISTORY | 0.412076 / 0.436651 / 0.349408 | -0.001986 | 0.518078 / 0.519382 / 0.515976 | 0.237135 / 0.242357 / 0.226209 | 0.020535 / 0.025721 / 0.084835 |

Frozen attribution classification:

| family | removal helps | removal hurts | mean PR delta | status |
|---|---:|---:|---:|---|
| STRUCTURE | 0 | 3 | -0.013006 | CONTRIBUTES_DIRECTIONALLY |
| MOMENTUM | 0 | 3 | -0.007881 | CONTRIBUTES_DIRECTIONALLY |
| VOLUME_LIQUIDITY | 1 | 2 | -0.000896 | CONTRIBUTES_DIRECTIONALLY |
| VOLATILITY | 1 | 2 | -0.001878 | CONTRIBUTES_DIRECTIONALLY |
| HISTORY | 1 | 2 | -0.001986 | CONTRIBUTES_DIRECTIONALLY |

All five statuses follow the frozen rule. No new subset or feature selection
was created.

## Within-date ranking diagnostic

HGB raw scores were ranked within each validation date. Rows and TP rates are
listed Q1 through Q5.

| fold | rows Q1-Q5 | TP rate Q1-Q5 | Q5-Q1 | Q5 lift vs base | Q5 > Q1 |
|---|---|---|---:|---:|---|
| F1 | 5,627 / 5,672 / 5,679 / 5,672 / 5,730 | 0.365203 / 0.386812 / 0.382110 / 0.389633 / 0.413613 | 0.048409 | 0.026051 | yes |
| F2 | 5,115 / 5,162 / 5,155 / 5,162 / 5,213 | 0.406843 / 0.431809 / 0.399224 / 0.405657 / 0.426242 | 0.019399 | 0.012246 | yes |
| F3 | 5,382 / 5,439 / 5,431 / 5,439 / 5,487 | 0.295987 / 0.308513 / 0.306021 / 0.339584 / 0.375615 | 0.079628 | 0.050315 | yes |
| POOLED | 16,124 / 16,273 / 16,265 / 16,273 / 16,430 | 0.355309 / 0.374916 / 0.362127 / 0.377988 / 0.404930 | 0.049621 | 0.029781 | yes |

The frozen directional quintile gate passed in all three folds.

## Causal regime diagnostics

Tertile thresholds were derived from training dates only and then frozen for
each validation fold.

| fold | axis | low threshold | high threshold |
|---|---|---:|---:|
| F1 | TREND | -0.029599499 | -0.006060606 |
| F1 | VOLATILITY | 0.040481030 | 0.045152160 |
| F2 | TREND | -0.025523869 | -0.007211859 |
| F2 | VOLATILITY | 0.039757412 | 0.044126496 |
| F3 | TREND | -0.024587028 | -0.004756819 |
| F3 | VOLATILITY | 0.038880915 | 0.043062484 |

All slices had at least 1,000 rows and were flagged `OK`.

| fold | axis/regime | rows | positive | PR-AUC | ROC-AUC | Brier | ECE | mean probability |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| F1 | TREND_LOW | 4,697 | 0.403875 | 0.456410 | 0.549425 | 0.239947 | 0.033753 | 0.381268 |
| F1 | TREND_MID | 15,668 | 0.378478 | 0.404081 | 0.512993 | 0.234899 | 0.015961 | 0.378620 |
| F1 | TREND_HIGH | 8,015 | 0.395758 | 0.403851 | 0.500716 | 0.239579 | 0.026802 | 0.376303 |
| F1 | VOLATILITY_LOW | 24,164 | 0.380732 | 0.397116 | 0.505608 | 0.235686 | 0.018599 | 0.378033 |
| F1 | VOLATILITY_MID | 3,055 | 0.420622 | 0.485586 | 0.569850 | 0.243495 | 0.047631 | 0.380230 |
| F1 | VOLATILITY_HIGH | 1,161 | 0.442722 | 0.519108 | 0.551092 | 0.248623 | 0.068771 | 0.381328 |
| F2 | TREND_LOW | 7,213 | 0.452100 | 0.473042 | 0.499765 | 0.251854 | 0.065011 | 0.387090 |
| F2 | TREND_MID | 7,858 | 0.389412 | 0.401032 | 0.507030 | 0.237704 | 0.018022 | 0.388143 |
| F2 | TREND_HIGH | 10,736 | 0.406390 | 0.414639 | 0.506477 | 0.241437 | 0.021592 | 0.389505 |
| F2 | VOLATILITY_LOW | 17,583 | 0.445715 | 0.446764 | 0.496214 | 0.250297 | 0.056709 | 0.389006 |
| F2 | VOLATILITY_MID | 6,193 | 0.340384 | 0.349883 | 0.475352 | 0.226936 | 0.057354 | 0.387307 |
| F2 | VOLATILITY_HIGH | 2,031 | 0.363860 | 0.417977 | 0.533016 | 0.231509 | 0.037429 | 0.386686 |
| F3 | TREND_LOW | 13,482 | 0.335039 | 0.368080 | 0.535256 | 0.227915 | 0.075449 | 0.410488 |
| F3 | TREND_MID | 5,187 | 0.231733 | 0.256666 | 0.530541 | 0.208888 | 0.176432 | 0.408166 |
| F3 | TREND_HIGH | 8,509 | 0.366906 | 0.424159 | 0.546405 | 0.232798 | 0.049166 | 0.407849 |
| F3 | VOLATILITY_LOW | 14,013 | 0.333191 | 0.382215 | 0.544817 | 0.226840 | 0.074754 | 0.407945 |
| F3 | VOLATILITY_MID | 7,596 | 0.379937 | 0.416851 | 0.539795 | 0.235787 | 0.031279 | 0.410226 |
| F3 | VOLATILITY_HIGH | 5,569 | 0.230921 | 0.265163 | 0.535227 | 0.209623 | 0.180127 | 0.411048 |

The weakest calibration slices are F3 `TREND_MID` and F3
`VOLATILITY_HIGH`, with ECE `0.176432` and `0.180127`; both materially
overpredict relative to their observed positive rates. Their PR-AUC remains
above prevalence, so this is a calibration/stability concern rather than a
reversed ranking claim. No >=1,000-row slice had PR-AUC below prevalence.

## Calibration experiment

All candidates used the identical HGB ranking model; only the probability
mapping changed.

| fold | calibrator | rows | positive | mean probability | PR-AUC | ROC-AUC | Brier | ECE | log loss | abs gap |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F1 | NATIVE | 28,380 | 0.387562 | 0.411817 | 0.413738 | 0.515887 | 0.241788 | 0.060364 | 0.677146 | 0.024256 |
| F1 | PLATT | 28,380 | 0.387562 | 0.378404 | 0.413738 | 0.515887 | 0.237056 | 0.017066 | 0.667038 | 0.009158 |
| F1 | ISOTONIC | 28,380 | 0.387562 | 0.379204 | 0.396636 | 0.510701 | 0.237097 | 0.014824 | 0.667180 | 0.008358 |
| F2 | NATIVE | 25,807 | 0.413996 | 0.335100 | 0.425449 | 0.502705 | 0.253468 | 0.087692 | 0.704571 | 0.078896 |
| F2 | PLATT | 25,807 | 0.413996 | 0.388415 | 0.425449 | 0.502705 | 0.243212 | 0.026906 | 0.679557 | 0.025581 |
| F2 | ISOTONIC | 25,807 | 0.413996 | 0.388432 | 0.420105 | 0.501606 | 0.242918 | 0.025565 | 0.682370 | 0.025565 |
| F3 | NATIVE | 27,178 | 0.325300 | 0.329886 | 0.364907 | 0.538533 | 0.220105 | 0.034782 | 0.632516 | 0.004586 |
| F3 | PLATT | 27,178 | 0.325300 | 0.409218 | 0.364907 | 0.538533 | 0.225813 | 0.083919 | 0.644276 | 0.083919 |
| F3 | ISOTONIC | 27,178 | 0.325300 | 0.409274 | 0.344890 | 0.523872 | 0.225534 | 0.083974 | 0.643582 | 0.083974 |

Pooled calibration metrics:

| calibrator | rows | positive | mean probability | PR-AUC | ROC-AUC | Brier | weighted ECE | log loss | gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NATIVE | 81,365 | 0.375149 | 0.360117 | 0.402897 | 0.523779 | 0.238250 | 0.060487 | 0.670937 | 0.015032 |
| PLATT | 81,365 | 0.375149 | 0.391872 | 0.374347 | 0.485964 | 0.235253 | 0.042517 | 0.663406 | 0.016723 |
| ISOTONIC | 81,365 | 0.375149 | 0.392175 | 0.366639 | 0.474458 | 0.235081 | 0.041328 | 0.664115 | 0.017026 |

The frozen selection rule selected **ISOTONIC** because its pooled Brier
`0.235081` was lowest; no manual override was applied.

## Calibration-readiness gate

Base-rate pooled Brier was `0.234695`; base-rate weighted ECE was `0.030241`.

| condition | result |
|---|---|
| selected pooled Brier beats base-rate | **false** (`0.235081` > `0.234695`) |
| selected pooled weighted ECE beats base-rate | **false** (`0.041328` > `0.030241`) |
| selected prevalence gap better than base-rate in at least 2/3 folds | **false**; 1/3 folds |
| all probability metrics finite | **true** |
| `holdout_outcome_accessed=false` | **true** |
| calibration-ready | **false** |

Therefore the automatic final state is
`STAGE4_RANKING_GO_CALIBRATION_BLOCKED`.

## External runtime artifacts

Runtime directory (not committed):

`D:\Documents\Project\idx-trade-data-gate-20260808v\stage4_development_v1_20260809`

All generated artifact hashes:

| artifact | SHA-256 |
|---|---|
| `stage4_reference_fold_metrics.csv` | `7f33c22274f5b4559e27c59d80a3aca18975917add23e1fbd1d2c40b8cc2272e` |
| `stage4_reference_pooled_metrics.csv` | `16b78f69d0fce46ea91bdee5492a75e026d9bf232e417474b84c9e49938eebf0` |
| `stage4_ablation_fold_metrics.csv` | `50de131294f71c0917b23caa3786ce320778532152a152a761b711c8ff2a566d` |
| `stage4_ablation_oof_predictions.parquet` | `24ef5def701e0a6ae2c1a8a8b12bfd81b6e2cf3a6860b2983f54781f49b653a5` |
| `stage4_feature_attribution.csv` | `291918435c58edf78f0602475984fabeb4cbb0fd7ce4350c4ee02b415983cf2a` |
| `stage4_cross_sectional_quintile_rows.parquet` | `57f8dfa0f3dca11abe6577abd12c0cff471d1c9c33c463b3efbc640234cbff3b` |
| `stage4_cross_sectional_quintile_summary.csv` | `ade6c2dd9377ed90ec897dfeabb63f545def7b8cb1607bdd0743a7e02e7c9b76` |
| `stage4_calibration_fold_metrics.csv` | `44f2b3136a7f7089164ebdcf76944cd26d754f4a0f8aeb6fac2251fa0f99f1a7` |
| `stage4_calibration_oof_predictions.parquet` | `964d3bdbb39b3069deb8328b981150a634d9c2ba780759e9294baccd2e1869b5` |
| `stage4_calibration_pooled_metrics.csv` | `6ec8e1ff86f3f35a87e4db535d826c138bb498f36bf1439e53e8b5f70c45a2f9` |
| `stage4_regime_thresholds.csv` | `31151b12b9dc382d9674bc2f198b45f0be494feec10b1a201957931e8207d087` |
| `stage4_regime_metrics.csv` | `8dfd414012822c7bf7938b1fc03276921cd07d7871e9afac02792c829dea7b14` |
| `stage4_development_summary.json` | `1d904314e01c1a03b1ffce1cdb6ff5cec4be4caa8723ae0b7413927258be3155` |

The runner summary reported the same hashes for every generated artifact.
Runtime parquet/CSV outputs remain outside Git. This checkpoint is the
documentation-only record for independent ChatGPT review.

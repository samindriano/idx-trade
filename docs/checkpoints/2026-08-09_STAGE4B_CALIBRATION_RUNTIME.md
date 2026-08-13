# Stage-4B V1 Causal Calibration Runtime

Date: 2026-08-09 (Asia/Jakarta)

Branch: `research/idx-stage4b-calibration-v1`

Code head used: `607fc8045711892960bad68135da842289222700`

Automatic status: **STAGE4B_CALIBRATION_STILL_BLOCKED**

This was an execution-only run of the frozen Stage-4B causal prior-shift
calibration runtime. No HGB refit, feature/model change, label/universe
change, fold change, external data, market redownload, Open synthesis,
holdout inspection, Stage 5, `IDX-VAL-002`, paper/live trading, or main merge
was performed.

## Admission and parent safety

- Python: `3.13.5`
- NumPy: `2.4.2`
- pandas: `2.3.3`
- pyarrow: `23.0.1`
- scikit-learn: `1.8.0`
- seed: `42`
- full pytest: **198 passed, 0 failed**; three existing pandas/NumPy
  `FutureWarning` messages
- parent Stage-4 decision:
  `STAGE4_RANKING_GO_CALIBRATION_BLOCKED`
- `holdout_outcome_accessed=false`
- locked holdout start: index `1009`, date `2025-07-15`
- exact official calendar: 1,260 sessions, `2021-04-29` through `2026-07-31`
- calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

Frozen input hashes:

| input | SHA-256 |
|---|---|
| Stage-3 primary model table | `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189` |
| Stage-4 calibration OOF predictions | `964d3bdbb39b3069deb8328b981150a634d9c2ba780759e9294baccd2e1869b5` |
| Stage-4 development summary | `1d904314e01c1a03b1ffce1cdb6ff5cec4be4caa8723ae0b7413927258be3155` |

## Frozen causal contract

Primary candidate: `ISOTONIC_PRIOR_SHIFT_60`.

For prediction session `t`, the maturity cutoff is `t - 10` official
sessions. The recent prior uses the 60 official signal sessions ending at
that cutoff and only resolved `TP_FIRST` / `SL_FIRST` primary-model rows.
Minimum recent resolved rows is 1,000. The 126-session candidate is
sensitivity-only and cannot replace the primary 60-session decision.

## Fold metrics

All candidates are reported with rows, positive rate, mean probability,
absolute prevalence gap, Brier, ECE, log loss, PR-AUC, and ROC-AUC.

| fold | candidate | rows | positive | mean prob | gap | Brier | ECE | log loss | PR-AUC | ROC-AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F1 | STATIC_BASE_RATE | 28,380 | 0.387562 | 0.386984 | 0.000578 | 0.237358 | 0.000578 | 0.667646 | 0.387562 | 0.500000 |
| F1 | STATIC_ISOTONIC | 28,380 | 0.387562 | 0.379204 | 0.008358 | 0.237097 | 0.008358 | 0.667180 | 0.396636 | 0.510701 |
| F1 | CAUSAL_PRIOR_ONLY_60 | 28,380 | 0.387562 | 0.390284 | 0.002723 | 0.238877 | 0.031738 | 0.670900 | 0.384960 | 0.483880 |
| F1 | ISOTONIC_PRIOR_SHIFT_60 | 28,380 | 0.387562 | 0.389852 | 0.002291 | 0.238561 | 0.034284 | 0.670298 | 0.395040 | 0.499770 |
| F1 | ISOTONIC_PRIOR_SHIFT_126 | 28,380 | 0.387562 | 0.391475 | 0.003914 | 0.238343 | 0.036819 | 0.669777 | 0.377854 | 0.478812 |
| F2 | STATIC_BASE_RATE | 25,807 | 0.413996 | 0.388354 | 0.025642 | 0.243261 | 0.025642 | 0.679654 | 0.413996 | 0.500000 |
| F2 | STATIC_ISOTONIC | 25,807 | 0.413996 | 0.388432 | 0.025565 | 0.242918 | 0.026151 | 0.681032 | 0.420105 | 0.501606 |
| F2 | CAUSAL_PRIOR_ONLY_60 | 25,807 | 0.413996 | 0.387901 | 0.026095 | 0.245164 | 0.026095 | 0.683740 | 0.400827 | 0.468059 |
| F2 | ISOTONIC_PRIOR_SHIFT_60 | 25,807 | 0.413996 | 0.387826 | 0.026170 | 0.244830 | 0.026915 | 0.685136 | 0.411153 | 0.474434 |
| F2 | ISOTONIC_PRIOR_SHIFT_126 | 25,807 | 0.413996 | 0.380664 | 0.033333 | 0.244328 | 0.041450 | 0.684025 | 0.392073 | 0.456110 |
| F3 | STATIC_BASE_RATE | 27,178 | 0.325300 | 0.390884 | 0.065584 | 0.223781 | 0.065584 | 0.640049 | 0.325300 | 0.500000 |
| F3 | STATIC_ISOTONIC | 27,178 | 0.325300 | 0.409274 | 0.083974 | 0.225534 | 0.084089 | 0.643582 | 0.344890 | 0.523872 |
| F3 | CAUSAL_PRIOR_ONLY_60 | 27,178 | 0.325300 | 0.394713 | 0.069413 | 0.225283 | 0.069413 | 0.642579 | 0.339403 | 0.534406 |
| F3 | ISOTONIC_PRIOR_SHIFT_60 | 27,178 | 0.325300 | 0.394299 | 0.068999 | 0.224167 | 0.069115 | 0.640141 | 0.358007 | 0.541733 |
| F3 | ISOTONIC_PRIOR_SHIFT_126 | 27,178 | 0.325300 | 0.408341 | 0.083041 | 0.224126 | 0.083290 | 0.640533 | 0.359805 | 0.544385 |

## Pooled metrics

| candidate | rows | positive | mean prob | gap | Brier | ECE | log loss | PR-AUC | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| STATIC_BASE_RATE | 81,365 | 0.375149 | 0.388721 | 0.013572 | 0.234695 | 0.013572 | 0.662236 | 0.358384 | 0.470722 |
| STATIC_ISOTONIC | 81,365 | 0.375149 | 0.392175 | 0.017026 | 0.235081 | 0.036609 | 0.663691 | 0.366639 | 0.474458 |
| CAUSAL_PRIOR_ONLY_60 | 81,365 | 0.375149 | 0.391008 | 0.015859 | 0.236330 | 0.024609 | 0.665513 | 0.371303 | 0.506386 |
| ISOTONIC_PRIOR_SHIFT_60 | 81,365 | 0.375149 | 0.390695 | 0.015546 | 0.235741 | 0.026303 | 0.664931 | 0.383698 | 0.511816 |
| ISOTONIC_PRIOR_SHIFT_126 | 81,365 | 0.375149 | 0.393680 | 0.018531 | 0.235493 | 0.029126 | 0.664528 | 0.371123 | 0.481658 |

The primary 60-session shift beat `CAUSAL_PRIOR_ONLY_60` on pooled Brier
(`0.235741 < 0.236330`), but did not beat static base-rate or static
isotonic. The 126-session result is sensitivity only.

## Causal prior audit

The audit contains 756 rows: 378 validation dates for each of the 60- and
126-session windows.

| window | audit rows | recent resolved rows min/max | recent prior min/max | failed audit rows | prediction index - maturity index |
|---:|---:|---:|---:|---:|---:|
| 60 | 378 | 12,097 / 13,917 | 0.314968 / 0.501114 | 0 | exactly 10 for every row |
| 126 | 378 | 25,805 / 28,511 | 0.354013 / 0.438837 | 0 | exactly 10 for every row |

For every row, `max_prior_source_signal_date` equals the maturity cutoff date;
there were zero source-after-cutoff rows. All minimum-row requirements were
satisfied. Therefore `causal_audit_pass=true` for both windows.

## Primary readiness gate

| condition | result |
|---|---|
| pooled Brier < static base-rate Brier | **false**: `0.235741` > `0.234695` |
| pooled Brier < causal-prior-only-60 Brier | **true**: `0.235741` < `0.236330` |
| pooled Brier < static isotonic Brier | **false**: `0.235741` > `0.235081` |
| pooled ECE < static base-rate ECE | **false**: `0.026303` > `0.013572` |
| prevalence gap better than static base-rate in at least 2/3 folds | **false**: 0 folds |
| all metrics finite | **true** |
| all causal audits pass | **true** |
| `holdout_outcome_accessed=false` | **true** |

The final automatic status is **`STAGE4B_CALIBRATION_STILL_BLOCKED`**.

## External runtime artifacts

Runtime directory (not committed):

`D:\Documents\Project\idx-trade-data-gate-20260808v\stage4b_calibration_v1_20260809`

| artifact | SHA-256 |
|---|---|
| `stage4b_candidate_oof_predictions.parquet` | `5434e40f53bda8d157a6b4d85a6f2717b9f25144946624b1dd31a577442ab30f` |
| `stage4b_fold_reference_priors.csv` | `b54240c64bd7f6dc9acc07857b4a05130464902be28c82af23916cdf2b729e6f` |
| `stage4b_causal_prior_audit.csv` | `b9de002be3014300b04848c6fc3746ebc9b78bf84077e1d74db12de0d6e6dcdf` |
| `stage4b_fold_metrics.csv` | `282b94789667b4d5cb9c519180fde7357f267e36c1bd4a884e8e266ba7e31be2` |
| `stage4b_pooled_metrics.csv` | `b2d50914b980dbd1aff57f623cba69d28a79a53a6d804d26c908272f7e9dea3f` |
| `stage4b_development_summary.json` | `f9cbce089c21debd6420943ebf5cd647fc41942e4f210964ddbb5d165d10ebb7` |

All six hashes match the runner summary. Runtime parquet/CSV outputs remain
outside Git. Stop for independent ChatGPT review; this result does not
authorize Stage 5 or holdout access.

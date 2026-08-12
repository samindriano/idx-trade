# STAGE3 development runtime - advancement rule met

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage3-v1`
Code head: `4c484b087aff592234dbe9905213e9d83b2f2611`

## Status

`STAGE3_RUNTIME_COMPLETE_ADVANCEMENT_RULE_MET`

This is frozen Stage-3 development OOF evidence only. It is not final OOS
performance and does not authorize Stage 4, locked-holdout inspection,
`IDX-VAL-002`, deployment, paper trading, or a merge to `main`.

## Test and admission result

- full pytest: **184 passed, 0 failed**;
- warnings: three existing pandas/NumPy deprecation warnings;
- input panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- research manifest SHA-256:
  `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`;
- manifest verification: `valid=true`, 15/15, no mismatches;
- official calendar: 1,260 sessions, `2021-04-29 -> 2026-07-31`;
- max signal session read: 942 (`2025-03-20`);
- max future source session read: 962 (`2025-04-29`);
- locked holdout start: session 1009 (`2025-07-15`);
- `holdout_outcome_accessed=false`;
- primary V1 parameters unchanged: H10, ATR14, SL 1.0 ATR, RR 1.5, IDR 1bn.

Specification hashes recorded by the runner:

| document | SHA-256 |
|---|---|
| `RESEARCH_SPECIFICATION_V1` | `73c252f4d5724320bcf42a47c6f604735ba000b622e8514660dc62fea1aab51e` |
| `VALIDATION_PLAN_V1` | `5e42e8289c86c37a27602731a2d2c51b299d4ff2ac36e20f43cc234bd73afb3f` |
| `VALIDATION_THREAT_MODEL_V1` | `c1112d55ba12658d9be3e1ba3d9c6aa7c62679ffdb7e27c02fb0a84b5e823163` |
| `STAGE3_IMPLEMENTATION_PLAN_V1` | `4973b76aa8a5fe0644ee41326f2e314b5935101f7b1f7589dca02b26da3de892` |

Dependencies: Python 3.13.5, NumPy 2.4.2, pandas 2.3.3, pyarrow 23.0.1,
scikit-learn 1.8.0, seed 42.

## Runtime output

Runtime artifacts are outside Git:

`D:\Documents\Project\idx-trade-data-gate-20260808v\stage3_development_v1_20260809`

Summary SHA-256:
`979c56be43e2fdc5c0502e1b1625d74dbcab6ba28f097338575479739baa029f`

## Label diagnostics

All H5/H10/H20 ledgers contain 712,325 full valid candidate rows. Percentages
are percentages of that horizon ledger. `UNRESOLVED_HORIZON_END` is zero for
development because the runner stops signal rows at 942 and reads through 962.

| status | H5 rows | H5 % | H10 rows | H10 % | H20 rows | H20 % |
|---|---:|---:|---:|---:|---:|---:|
| `TP_FIRST` | 152,295 | 21.3800% | 197,910 | 27.7837% | 220,450 | 30.9480% |
| `SL_FIRST` | 254,261 | 35.6945% | 315,049 | 44.2283% | 344,173 | 48.3168% |
| `AMBIGUOUS_SAME_BAR` | 6,520 | 0.9153% | 6,974 | 0.9790% | 6,921 | 0.9716% |
| `NO_BARRIER_HIT` | 227,628 | 31.9556% | 107,189 | 15.0478% | 38,242 | 5.3686% |
| `UNRESOLVED_PATH` | 26,881 | 3.7737% | 40,463 | 5.6804% | 57,799 | 8.1141% |
| `UNRESOLVED_HORIZON_END` | 0 | 0.0000% | 0 | 0.0000% | 0 | 0.0000% |
| `INVALID_BARRIER` | 44,740 | 6.2808% | 44,740 | 6.2808% | 44,740 | 6.2808% |

Primary H10 resolved binary model rows are `197,910 + 315,049 = 208,375`.
No secondary horizon was used to replace H10.

## Universe and coverage

| population | rows | share of full valid |
|---|---:|---:|
| full valid candidate rows | 712,325 | 100.0000% |
| history-qualified rows | 692,648 | 97.2376% |
| primary broad-liquid rows | 244,761 | 34.3609% |
| resolved H10 binary model rows | 208,375 | 29.2528% |

Primary drop-reason histogram:

| drop reason | rows | share |
|---|---:|---:|
| `NOT_PRIMARY_LIQUID_UNIVERSE` | 467,564 | 65.6391% |
| `ADMITTED` | 208,375 | 29.2528% |
| `NO_BARRIER_HIT` | 33,199 | 4.6607% |
| `UNRESOLVED_PATH` | 1,569 | 0.2203% |
| `AMBIGUOUS_SAME_BAR` | 1,161 | 0.1630% |
| `INVALID_BARRIER` | 457 | 0.0642% |

Date-level candidate distribution:

- full valid rows per date: 640 minimum, 857 maximum;
- history-qualified rows: 0 during warm-up, then 560 on the first qualified
  date `2021-06-02`, maximum 849;
- primary broad-liquid rows: 0 during warm-up, then 228 on `2021-06-02`,
  maximum 307;
- top-100 sensitivity total: 92,300 rows; top-300 sensitivity total:
  276,900 rows;
- no unexplained material shift after warm-up: the largest full-valid
  day-to-day change was 776 -> 729 (-47) on `2023-03-16`, history-qualified
  change was -41, and primary-liquid changes after warm-up were at most 6
  rows. The initial zero-to-qualified jump is the frozen 60-session/20-row
  history rule.

## Fold metrics

Rows are resolved validation rows. `positive_rate` is the observed TP_FIRST
rate; `mean_probability` is the model prediction mean.

| fold | model | rows | positive rate | PR-AUC | ROC-AUC | Brier | ECE | mean probability |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| F1 | base_rate | 28,380 | 0.3875617 | 0.3875617 | 0.5000000 | 0.2373580 | 0.0005780 | 0.3869837 |
| F1 | momentum_20 | 28,380 | 0.3875617 | 0.3994493 | 0.5132914 | 0.2373242 | 0.0103803 | 0.3802704 |
| F1 | logistic_compact | 28,380 | 0.3875617 | 0.3962291 | 0.5095328 | 0.2379520 | 0.0259746 | 0.3642602 |
| F1 | hist_gradient_boosting | 28,380 | 0.3875617 | 0.4137378 | 0.5158869 | 0.2370560 | 0.0170657 | 0.3784041 |
| F2 | base_rate | 25,807 | 0.4139962 | 0.4139962 | 0.5000000 | 0.2432609 | 0.0256423 | 0.3883539 |
| F2 | momentum_20 | 25,807 | 0.4139962 | 0.4098292 | 0.4925741 | 0.2434502 | 0.0275172 | 0.3884129 |
| F2 | logistic_compact | 25,807 | 0.4139962 | 0.4168723 | 0.5039675 | 0.2438405 | 0.0350497 | 0.3797913 |
| F2 | hist_gradient_boosting | 25,807 | 0.4139962 | 0.4254488 | 0.5027053 | 0.2432120 | 0.0269058 | 0.3884154 |
| F3 | base_rate | 27,178 | 0.3252999 | 0.3252999 | 0.5000000 | 0.2237811 | 0.0655837 | 0.3908836 |
| F3 | momentum_20 | 27,178 | 0.3252999 | 0.3288949 | 0.4908860 | 0.2272428 | 0.0870010 | 0.4103727 |
| F3 | logistic_compact | 27,178 | 0.3252999 | 0.3502024 | 0.5234208 | 0.2253782 | 0.0783970 | 0.4036969 |
| F3 | hist_gradient_boosting | 27,178 | 0.3252999 | 0.3649071 | 0.5385334 | 0.2258125 | 0.0839185 | 0.4092184 |

Reliability diagnostics use fixed calibration-derived bins. The constant
base-rate model has one populated bin; momentum, logistic, and HGB have ten
populated bins per fold. Fold ECE is reported above. Pooled ECE is 0.0302414
base-rate, 0.0414090 momentum, 0.0463635 logistic, and 0.0425173 HGB.

## Pooled development OOF

| model | rows | PR-AUC | ROC-AUC | Brier | weighted ECE | positive rate | mean probability |
|---|---:|---:|---:|---:|---:|---:|---:|
| base_rate | 81,365 | 0.3583836 | 0.4707216 | 0.2346952 | 0.0302414 | 0.3751490 | 0.3887209 |
| momentum_20 | 81,365 | 0.3532776 | 0.4705655 | 0.2358998 | 0.0414090 | 0.3751490 | 0.3929079 |
| logistic_compact | 81,365 | 0.3646460 | 0.4783577 | 0.2356197 | 0.0463635 | 0.3751490 | 0.3823591 |
| hist_gradient_boosting | 81,365 | 0.3743467 | 0.4859640 | 0.2352529 | 0.0425173 | 0.3751490 | 0.3918722 |

Advancement rule: `logistic_compact` met it on F2/F3; HGB met it on F1/F2/F3.
This rule is directional PR-AUC only. Pooled Brier/ECE did not uniformly
improve over base-rate, which is a remaining review concern rather than a
reason to retune V1.

## Economic-like research diagnostics

These are signal-research diagnostics, not execution PnL. H10 summaries by
status:

| status | rows | MFE mean/median | MAE mean/median | terminal return mean/median | research R mean/median |
|---|---:|---|---|---|---|
| `TP_FIRST` | 80,038 | 0.16217 / 0.11494 | -0.03290 / -0.01887 | 0.06913 / 0.04459 | 1.52689 / 1.19149 |
| `SL_FIRST` | 128,337 | 0.04371 / 0.02540 | -0.10817 / -0.08602 | -0.05180 / -0.04280 | -1.12626 / -1.07143 |
| `NO_BARRIER_HIT` | 33,199 | 0.05036 / 0.04167 | -0.03507 / -0.02844 | -0.00054 / 0.00000 | 0.02447 / 0.00000 |
| `AMBIGUOUS_SAME_BAR` | 1,161 | 0.17145 / 0.11650 | -0.12224 / -0.08257 | -0.00920 / -0.01460 | -0.10181 / -0.41176 |

## Output artifact hashes

All 15 runner-declared artifacts exist and match their recorded SHA-256; zero
mismatches. Runtime parquet/CSV/model artifacts are not committed.

| artifact | SHA-256 |
|---|---|
| `stage3_baseline_features_development.parquet` | `f16d77caa6642d0aba8c0a39eda5b2d32e53f17717b149f5f0637eeacac80772` |
| `stage3_primary_model_table_development.parquet` | `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189` |
| `stage3_oof_predictions_development.parquet` | `32b793fb75d111a5b6880cbc2ac4016838506d640245c04d748ea0bb6dd639a1` |
| `stage3_fold_metrics.csv` | `37ac7a1a58dee49aca5e7fbebecfcec71d8a6b56a73d33e478ccbead0768e52b` |
| `stage3_pooled_oof_metrics.csv` | `05979dbaacbe3e96c35f696295a956ee9fe65120fbded18710b4d86fe205c29e` |
| `stage3_reliability_bins.csv` | `9258a91fb10cf8d03ca5b609e1f635034f068d47d1e3cad10a34e8dbbcb9657c` |
| `stage3_candidate_counts_by_date.csv` | `f05603c30ea96d7c5275458f7ba694125cd44890335ffcbfc1a93f4e879a2f44` |
| `stage3_primary_drop_reason_ledger.parquet` | `1c7b4ae9d325d66b18c6075f306ff3c2c8f922aa3a88d322f00d698cc1e2cf4a` |
| `stage3_primary_drop_reason_summary.csv` | `2780b12d09ae2a1664a04f4992c28204af0cdf616f5c54194b5daa54928151e7` |
| `stage3_primary_excursion_summary.csv` | `fd0d0defbeb86ebfef6a53b96df62378feb66a16366d3909b40d816968f97d04` |
| `stage3_fold_boundary_audit.json` | `7f2434bca67b06242945fd766669d46cf55fc1e7760179e6618bd6987e7ae10b` |
| `stage3_calibration_bin_edges.json` | `3c169ec62fd948007433de19a7525d9797913115a6d4e4e6f3e144bcd93f6c24` |
| `stage3_labels_h5_development.parquet` | `89dab11ae5ec9ebeee3361497156f67b801a00717f495eb4ae1ad5b3f08086fb` |
| `stage3_labels_h10_development.parquet` | `eeb6a1b2e48d816131172a35462d55ba4f842eee39f3deb4b1f2540ec3b597e7` |
| `stage3_labels_h20_development.parquet` | `569b1d34c7ade47cc6b3076286eedd937897286507ad17c9fd44dc99c843d907` |

Summary artifact SHA-256:
`979c56be43e2fdc5c0502e1b1625d74dbcab6ba28f097338575479739baa029f`.

## Decision and stop point

The factual runtime status is `STAGE3_RUNTIME_COMPLETE_ADVANCEMENT_RULE_MET`.
Stop for independent ChatGPT review. Do not inspect the locked final holdout,
start Stage 4, tune V1, change the label/universe/folds, run `IDX-VAL-002`, or
merge to `main` in this task.

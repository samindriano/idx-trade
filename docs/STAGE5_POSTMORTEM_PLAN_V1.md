# Stage 5 Post-Mortem V1 — Frozen Diagnostic Plan

Date: 2026-08-09 (Asia/Jakarta)
Status: **FROZEN DIAGNOSTIC SCOPE — NO MODEL RESCUE**

## Purpose

Stage 5 ended with `STAGE5_RANKING_HOLDOUT_FAIL`. The consumed holdout may now be used for diagnosis and V2 hypothesis generation, but it is no longer independent evidence. This post-mortem asks only **why the frozen Ranking V1 behaved positively in HOLDOUT_A and negatively in HOLDOUT_B**.

This phase does not tune, refit, select, calibrate, or rescue any model. It does not authorize Stage 6, Probability V2, `IDX-VAL-002`, paper/live trading, execution-PnL claims, or merge to `main`.

## Frozen factual anchor

- Stage-5 runtime code: `05c2bb549b446da374c13937a41aa6732cf71ec0`
- Stage-5 summary SHA-256: `1a38171eead5a9c72de62da4f6ef486f35e3fba2e962c3b0bccac9fea033acd0`
- H10 prediction SHA-256: `9d850776c98c07e069b32d606ad510d94a26435659da86997f5302d765d8ee8c`
- signal panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- security-master SHA-256 used by Stage 5: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`
- holdout is consumed for `RANKING_V1_ONLY`; rerun is prohibited.

## Five bounded hypotheses

The diagnostic is limited to these predeclared hypotheses.

### H1 — Feature distribution drift

The frozen feature distribution may have shifted materially from HOLDOUT_A to HOLDOUT_B. For every frozen baseline feature report A/B mean, median, standard deviation, missingness, standardized mean difference, and median shift relative to pooled IQR.

### H2 — Feature/outcome relationship drift

A feature can retain a similar distribution while its relationship with `TP_FIRST` changes. For each frozen feature and each half, compute within-date percentile rank, rank-to-target correlation, and the target-rate spread between the top and bottom within-date feature quintiles. Report sign reversals explicitly; do not select a feature subset.

### H3 — Frozen score degradation is gradual or localized

Use six fixed temporal blocks, selected before any additional outcome inspection:

- A1: 1009–1048
- A2: 1049–1088
- A3: 1089–1129
- B1: 1130–1169
- B2: 1170–1209
- B3: 1210–1250

For each block report prevalence, HGB PR-AUC, ROC-AUC, PR-AUC minus prevalence, Q5-Q1, and top-decile lift. These blocks are descriptive only and cannot become new validation folds.

### H4 — Market/regime environment drift

Using the full primary-liquid universe at each signal date, not only resolved labels, create causal daily market summaries from existing frozen features: breadth of positive 5/20-session return, median 5/20-session return, median ATR/Close, median 20-session close position, median relative volume, and median relative regular-market value. Compare the A/B distributions. No regime threshold is optimized here.

### H5 — Broad-ranking failure versus top-tail behavior

Report HGB within-date decile outcome curves separately for HOLDOUT_A and HOLDOUT_B. This diagnoses whether the overall top-tail enrichment was stable or was produced mainly by one half. No new top-k cutoff may be declared validated from this analysis.

## Explicitly prohibited analyses

- no hyperparameter search;
- no retraining HGB/logistic/momentum on holdout outcomes;
- no new model family;
- no feature selection by holdout score;
- no alternative H5/H20 target rescue;
- no label/ATR/RR/SL optimization;
- no threshold/top-k optimization;
- no calibration fitting;
- no claim that a post-hoc subgroup is independently validated;
- no Stage-5 rerun.

## Interpretation rule

The post-mortem may establish a **diagnostic finding** or a **V2 hypothesis**, not a validated predictive claim. A future Ranking V2 must be designed separately and receive fresh forward evaluation strictly after `2026-07-31`.

## Required outputs

The diagnostic runner should emit only descriptive artifacts outside Git:

- `postmortem_fixed_block_metrics.csv`
- `postmortem_feature_drift_a_vs_b.csv`
- `postmortem_feature_target_relation_by_half.csv`
- `postmortem_market_regime_daily.csv`
- `postmortem_market_regime_a_vs_b.csv`
- `postmortem_hgb_deciles_by_half.csv`
- `postmortem_summary.json`

All outputs must be hashed. The result must then stop for independent ChatGPT interpretation before any V2 implementation.
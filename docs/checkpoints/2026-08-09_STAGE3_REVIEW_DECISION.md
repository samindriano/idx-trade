# Stage 3 independent review decision

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage3-v1`

Decision: `STAGE3_REVIEW_PASS_FOR_BOUNDED_STAGE4_RESEARCH`

This decision does not authorize locked-holdout inspection, Stage 5, execution-PnL claims, paper trading, live trading, Kelly sizing, `IDX-VAL-002`, or merge to `main`.

## Evidence supporting continuation

The pre-registered Stage-3 advancement rule is satisfied on development OOF:

- logistic compact beats both base-rate and momentum in F2/F3;
- HistGradientBoosting beats both in F1/F2/F3.

Mean fold PR-AUC:

- base-rate: 0.37562
- momentum: 0.37939
- logistic compact: 0.38777
- HistGradientBoosting: 0.40136

HistGradientBoosting mean PR-AUC improvement:

- +0.02575 versus base-rate;
- +0.02197 versus momentum.

Pooled OOF PR-AUC is also highest for HistGradientBoosting at 0.37435 versus 0.35838 base-rate, 0.35328 momentum, and 0.36465 logistic.

## Why this is not yet a probability-model PASS

Ranking evidence is stronger than calibration evidence.

Pooled Brier/ECE are not uniformly better than base-rate:

- base-rate: Brier 0.23470, ECE 0.03024
- momentum: Brier 0.23590, ECE 0.04141
- logistic: Brier 0.23562, ECE 0.04636
- HGB: Brier 0.23525, ECE 0.04252

F3 also shows visible prevalence/calibration drift. Therefore Stage 3 does not yet justify treating challenger output as a trustworthy calibrated `P(TP before SL)` estimate.

## Stage 4 boundary

Stage 4 may be designed as a separately frozen, bounded development-only research phase. It should prioritize:

1. robustness and ablation of the existing causal feature families;
2. regime/fold stability of ranking edge;
3. calibration improvement using training/development data only;
4. diagnostics for why F3 calibration drifts;
5. a small pre-registered challenger set rather than broad model/feature search.

The locked holdout must remain untouched until all Stage-4 choices are frozen and a separate authorization explicitly opens Stage 5.

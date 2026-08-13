# IDX Trade V1 Validation Plan

Status: STAGE-2 DESIGN; NO MODELLING AUTHORIZED
Date: 2026-08-09 (Asia/Jakarta)

This plan operationalizes `docs/RESEARCH_SPECIFICATION_V1.md`. It is a
validation contract, not an implementation or a model result. Any later code
must assert these invariants rather than relying on convention.

## 1. Validation objectives

The first cycle must answer whether a small causal feature set contains
out-of-sample information for the frozen 10-session first-touch barrier label.
Validation must also establish:

- no future data enters features, preprocessing, labels, or universe rules;
- the same-date cross-section remains grouped;
- overlapping forward paths are purged;
- ambiguous daily-bar paths remain explicit;
- probability calibration is evaluated separately from ranking;
- the final 252-session holdout is untouched until all development choices are
  frozen.

The input panel is the immutable, independently verified
`SIGNAL_RESEARCH_HLCV` artifact. No raw-price or calendar refetch is part of
this plan.

## 2. Admission and audit gates

Before generating a single feature or label, a future implementation must
write an immutable run manifest containing:

- source commit and specification hash;
- panel path, panel hash, and research manifest hash;
- exact official-session calendar hash;
- scope and ticker counts;
- split indices and dates;
- `H_primary=10` and `H_max=20`;
- barrier constants and ambiguity policy;
- universe rule and all thresholds;
- baseline/model family identifiers;
- seed and dependency versions where relevant.

Admission checks must fail closed on duplicate `security/date` rows, nonpositive
H/L/C/Volume, invalid H/L/C envelope, missing point-in-time scope, non-ACTIVE
state, unknown provenance, or an Open-dependent feature in the primary table.

No row from `UNKNOWN`, `NO_TRADE`, `SUSPENDED`, FCA/watchlist, delisted, or
another non-ACTIVE state may enter a feature, label, liquidity, training,
validation, or holdout denominator. A missing future bar is
`UNRESOLVED_PATH`, not a zero return and not a no-trade label.

## 3. Causal feature audit

For every feature, store or test:

1. the source columns;
2. the maximum source date allowed;
3. the rolling-window bounds in session-index space;
4. the fit rows for any imputer, scaler, rank, or encoder;
5. the missingness behavior.

Required automated tests include:

- shifting any input after `t` does not change a feature at `t`;
- removing the current row does not change features declared strictly prior;
- a centered rolling operation is rejected;
- a pivot's feature availability date is no earlier than its confirmation date;
- training-only preprocessing produces identical validation values when future
  rows are appended to the source table;
- primary feature names contain no `Open` dependency.

The baseline feature table must be small and versioned. Experimental S/R,
momentum, volatility, liquidity, and cross-sectional families are added one
family at a time with an ablation record.

## 4. Causal label audit

The label builder must operate in official-session index space, not weekday or
provider-row space. For each signal date `t`, it must:

- calculate ATR14 using only data through `t`;
- use `Close_t` only as `SIGNAL_REFERENCE_CLOSE`;
- inspect exactly the next H official sessions;
- require a valid ACTIVE future path for a resolved label;
- stop with an explicit status on the first missing/non-ACTIVE/UNKNOWN future
  session;
- record the first barrier date and same-bar ambiguity;
- emit MFE, MAE, and normalized close return only for complete paths.

Label regression fixtures must cover: TP first, SL first, no barrier, both
barriers on one bar, missing future bar, suspension interruption, delisting
boundary, invalid ATR, and horizon-end truncation. No fixture may assume
intraday ordering from daily High and Low.

## 5. Frozen temporal evaluation

The exact 1,260-session calendar is indexed 1 through 1,260:

- development: 1-1008, `2021-04-29 -> 2025-07-14`;
- locked holdout: 1009-1260, `2025-07-15 -> 2026-07-31`;
- holdout H=20 evaluation is available only through session 1240,
  `2026-07-03`; sessions 1241-1260 are a locked horizon-end buffer.

Development validation uses these three date-grouped folds:

| fold | train | gap | validation |
|---|---|---|---|
| F1 | 1-504 | 505-524 | 525-650 |
| F2 | 1-650 | 651-670 | 671-796 |
| F3 | 1-796 | 797-816 | 817-942 |

The gap is both the 20-session maximum-label purge and the explicit embargo
before the validation block. The fold runner must assert that no training
label interval intersects the corresponding validation signal dates and that
all preprocessing/calibration fit rows precede validation.

The development tail 943-1008 is not a fourth validation fold. It can only be
used for a later chronological development refit after fold decisions are
frozen. No holdout outcome is read during development.

## 6. Calibration procedure

For each fold:

1. split the training dates chronologically into a model-fit prefix and a
   calibration tail;
2. fit preprocessing and the raw model on the prefix only;
3. fit Platt/logistic calibration on the calibration tail only;
4. evaluate calibrated probabilities once on the untouched validation block;
5. optionally record isotonic as a pre-declared sensitivity only when class
   support is sufficient.

The exact internal split rule is 80% of available training dates for model fit
and the final 20% for calibration, rounded by official-session index and with
the same H=20 maturity rule. If either class is absent in the calibration tail,
the calibrated result is invalid for that fold and the failure is reported;
the base-rate baseline remains valid as a diagnostic.

All thresholds, bin edges, imputers, scalers, and model parameters are learned
inside the training portion. Calibration is never fitted on validation or
locked holdout outcomes.

## 7. Baseline and model comparison

Every fold reports the same resolved-label denominator for:

- constant training-fold base rate;
- 20-session momentum score;
- fixed compact logistic trend/structure baseline;
- one bounded tree challenger, if separately approved in Stage 3.

The primary comparison is mean fold PR-AUC. ROC-AUC, Brier, ECE, score-bucket
monotonicity, MFE/MAE, normalized R, and coverage are secondary reports. The
base-rate prevalence is the reference for PR-AUC interpretation.

An advancement decision requires directional improvement over both base-rate
and momentum in at least two of three development folds, with no silent loss
of coverage or relabelling of ambiguous/unresolved observations. This rule is
not a license to select a model using the holdout.

## 8. Report contract

Each development run must produce, at minimum:

- run manifest and specification hash;
- candidate counts by universe and date;
- label outcome table and unresolved/ambiguous rates;
- fold boundary assertion output;
- per-fold and pooled out-of-fold predictions;
- PR-AUC, ROC-AUC, Brier, ECE, reliability bins;
- fixed score bucket monotonicity;
- MFE/MAE and research-normalized-R summaries;
- baseline comparison;
- feature availability and leakage audit;
- exact dropped-row reasons;
- no holdout access assertion.

The locked holdout report is produced only after a separate approval confirms
that the specification, feature family, universe rule, calibration procedure,
and model choice are frozen. It is read once, archived immutably, and cannot
be used for repair or tuning.

## 9. Reproducibility and stop rules

The implementation must be deterministic for a fixed source commit, panel
hash, calendar, dependency lock, and seed. A run stops rather than continues
when it detects:

- panel or manifest hash drift;
- future-dated feature input;
- unknown or non-ACTIVE row admission;
- training/validation date overlap;
- label-path overlap not removed by purge;
- calibration fitted on validation/holdout;
- unexplained class or coverage changes;
- any attempt to use Open as a primary feature;
- a provider revision or artifact mismatch.

The plan does not define an execution strategy, PnL, trading signal, or
deployment. Those remain outside Stage 2.

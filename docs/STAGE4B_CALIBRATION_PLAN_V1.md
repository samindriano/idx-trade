# Stage 4B Calibration Plan V1 — Causal Prior-Shift Adaptation

Status: **FROZEN BEFORE STAGE-4B RUNTIME**
Date: 2026-08-09 (Asia/Jakarta)
Parent result: `STAGE4_RANKING_GO_CALIBRATION_BLOCKED`
Branch: `research/idx-stage4b-calibration-v1`

## 1. Why Stage 4B exists

Stage 4 preserved the HGB ranking signal but failed probability calibration readiness. The failure was concentrated in probability level drift rather than ranking collapse:

- HGB beat base-rate and momentum PR-AUC in F1/F2/F3;
- HGB Q5 > Q1 in F1/F2/F3;
- F3 `TREND_MID` and `VOLATILITY_HIGH` materially overpredicted, with ECE about 0.176 and 0.180;
- the selected static calibrator, ISOTONIC, still failed pooled Brier/ECE and prevalence-gap gates.

Stage 4B therefore tests one explicit diagnosis:

> The static score-to-probability map is not adapting to causal changes in the current TP-vs-SL base rate.

Stage 4B is **calibration-only**. It does not change ranking, labels, features, HGB parameters, universe, folds, or the final holdout boundary.

## 2. Immutable upstream inputs

Required exact artifacts:

- Stage-3 primary model table SHA-256: `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189`;
- Stage-4 calibration OOF predictions SHA-256: `964d3bdbb39b3069deb8328b981150a634d9c2ba780759e9294baccd2e1869b5`;
- Stage-4 development summary SHA-256: `1d904314e01c1a03b1ffce1cdb6ff5cec4be4caa8723ae0b7413927258be3155`;
- exact 1,260-session calendar;
- locked holdout start session 1009 / `2025-07-15`.

Numerical environment remains frozen to Stage 3/4:

- Python 3.13.5
- NumPy 2.4.2
- pandas 2.3.3
- pyarrow 23.0.1
- scikit-learn 1.8.0
- seed 42

## 3. Target semantics remain unchanged

The probability target remains the frozen Stage-3 binary target on the primary broad-liquid universe:

- positive: `TP_FIRST`;
- negative: `SL_FIRST`;
- H10 / ATR14 / SL 1.0 ATR / RR 1.5;
- ambiguous, no-barrier, unresolved-path, and invalid-barrier observations are not silently converted into binary labels.

Stage 4B does not redefine this target.

## 4. Ranking architecture is frozen

No HGB refit or feature/model search is performed in Stage 4B.

Use the exact Stage-4 OOF prediction artifact. The ranking signal is the frozen HGB raw score. Stage 4B changes only probability level calibration.

## 5. Primary calibration hypothesis

Stage 4 selected `ISOTONIC` by lowest pooled development Brier. Stage 4B keeps that static isotonic probability as the base calibrated probability and applies a deterministic prior-probability-shift correction.

For a static calibrated probability `p`, calibration-reference prior `pi_ref`, and causal recent prior `pi_recent`:

`odds_adjusted = odds(p) * odds(pi_recent) / odds(pi_ref)`

then convert adjusted odds back to probability.

All probabilities/priors are clipped only for numerical stability at `1e-6` and `1 - 1e-6`.

This is a fixed prior-shift correction, not a fitted Stage-4B model.

## 6. Causal recent prior

Primary window: **60 official signal sessions**.

For a prediction generated after close of session `t`, only binary labels from signal dates whose H10 outcome is fully mature may contribute.

Therefore:

- maturity cutoff = `t - 10 official sessions`;
- recent-prior window = the 60 official signal sessions ending at that maturity cutoff;
- only already-resolved primary-universe TP_FIRST / SL_FIRST rows are counted;
- minimum recent resolved rows = 1,000;
- if the minimum is not met, runtime fails closed rather than using future labels or an unregistered fallback.

Using a label that matures on session `t` for a new after-close signal on session `t` is causal: the full session-t market information is already known at the signal timestamp.

## 7. Reference prior

For each frozen fold, `pi_ref` is the positive rate of that fold's chronological **calibration tail**, using the same Stage-3/4 internal fit / H20 maturity-gap / calibration split.

It is computed from the frozen Stage-3 model table only. It is not estimated from validation outcomes.

## 8. Pre-registered candidates

Stage 4B reports exactly four probability series:

1. `STATIC_ISOTONIC`
   - exact Stage-4 isotonic OOF probability;

2. `CAUSAL_PRIOR_ONLY_60`
   - every security on date t receives `pi_recent_60`;
   - this is a critical adaptive-base-rate comparator;

3. `ISOTONIC_PRIOR_SHIFT_60`
   - **PRIMARY Stage-4B hypothesis**;
   - static Stage-4 isotonic probability adjusted by causal 60-session prior shift;

4. `ISOTONIC_PRIOR_SHIFT_126`
   - sensitivity diagnostic only;
   - identical mechanism with 126 official signal sessions;
   - it can never replace the primary 60-session hypothesis merely because its result is better.

No candidate selection/search is performed in Stage 4B.

## 9. Why a causal prior-only baseline is mandatory

A rolling prior can improve Brier score simply by tracking market-wide prevalence drift. Therefore Stage 4B must demonstrate that the score-conditioned probability adds value beyond causal prevalence adaptation itself.

`ISOTONIC_PRIOR_SHIFT_60` must be compared directly with `CAUSAL_PRIOR_ONLY_60`.

## 10. Metrics

For every fold and pooled OOF report:

- rows;
- positive rate;
- mean probability;
- absolute prevalence gap;
- Brier;
- log loss;
- ROC-AUC;
- PR-AUC;
- ECE using fixed equal-width decile bins `[0.0, 0.1, ..., 1.0]` for all Stage-4B candidates.

Fixed bins prevent candidate-specific bin definitions from obscuring direct ECE comparison.

Ranking metrics are diagnostic only: the prior-shift transform is monotonic within a date and must not be sold as a new ranking model.

## 11. Causality audit artifact

Persist one row per fold x validation date containing:

- prediction date;
- prediction session index;
- maturity-cutoff date/index;
- recent-prior window start/end;
- recent resolved row count;
- recent TP rate;
- reference calibration-tail TP rate;
- audit boolean proving the maximum prior-source signal date is not after the maturity cutoff.

Any causality-audit failure => `STAGE4B_RUNTIME_BLOCKED`.

## 12. Primary readiness gate

`STAGE4B_CALIBRATION_FREEZE_READY` requires ALL:

1. `ISOTONIC_PRIOR_SHIFT_60` pooled Brier < Stage-4B static base-rate comparator Brier;
2. `ISOTONIC_PRIOR_SHIFT_60` pooled Brier < `CAUSAL_PRIOR_ONLY_60` pooled Brier;
3. `ISOTONIC_PRIOR_SHIFT_60` pooled Brier < `STATIC_ISOTONIC` pooled Brier;
4. `ISOTONIC_PRIOR_SHIFT_60` pooled ECE < Stage-4B static base-rate comparator ECE;
5. prevalence gap improves versus the static base-rate comparator in at least 2 of 3 folds;
6. all metrics finite;
7. every causal prior audit passes;
8. `holdout_outcome_accessed=false`.

The static base-rate comparator must be recomputed on the same Stage-4B validation rows using each fold's frozen training prevalence, with the same fixed equal-width ECE bins.

The 126-session sensitivity cannot satisfy the gate on behalf of the 60-session primary hypothesis.

## 13. Decision states

### `STAGE4B_CALIBRATION_FREEZE_READY`

The primary causal 60-session prior-shift hypothesis passes every frozen gate. This allows a separate independent Stage-5 holdout-freeze review; it does **not** itself authorize holdout access.

### `STAGE4B_CALIBRATION_STILL_BLOCKED`

The primary hypothesis executes correctly but fails one or more readiness conditions. Do not open holdout. Any further calibration idea must be a separately documented research iteration.

### `STAGE4B_RUNTIME_BLOCKED`

Use for hash mismatch, environment drift, causality violation, schema mismatch, insufficient causal prior history, non-finite metrics, or any holdout access.

## 14. Explicit prohibitions

- no session >=1009 outcome access;
- no HGB refit/search/tuning;
- no feature changes;
- no label, H, RR, ATR, ambiguity, or universe changes;
- no regime-conditional hand-built corrections;
- no per-fold custom window selection;
- no choosing 126 over 60 after seeing results;
- no external data;
- no execution-PnL claims;
- no synthetic Open;
- no Kelly/sizing;
- no Stage 5 in the same run;
- no merge to main.

## 15. Interpretation boundary

Passing Stage 4B would mean the probability architecture has survived a development-only causal calibration test. It still would not prove final OOS calibration or profitability. Those claims require the untouched Stage-5 holdout and later forward shadow evaluation.

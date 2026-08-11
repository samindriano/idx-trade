# OHLCV O2 — Frozen Final Refit Specification

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-final-refit-v1`
Parent direction commit: `802ed22ba71b2345c643c56edd319ce62b0f6928`
Decision: `O2_FULL_3_FINAL_REFIT_AUTHORIZED`

## Purpose

Freeze the accepted O2 full-three geometry challenger and fit exactly one final historical model artifact for later independent forward evaluation.

This is not authorization to replace canonical V3-B or inspect any fresh-forward outcome.

## Frozen model identity

Use candidate identity:

`O2-GEOMETRY-FULL3-V1-CANDIDATE-001`

Feature order is exactly canonical V3-B 33 features followed by:

1. `open_position`
2. `open_to_high`
3. `open_to_low`

Expected 36-feature order SHA-256:

`a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`

No feature may be added, removed, reordered, transformed, or recomputed under a different definition.

## Frozen population

Use exactly the accepted common-support population from O1/O2/minimality:

- 278,168 rows;
- 729 tickers;
- common-support key SHA-256 `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`.

Load the accepted V3-B training table plus the exact Open coverage-gate geometry values. Do not rebuild a larger population from the panel and do not impute missing Open to enlarge the set.

All H10 labels must already be mature by the historical boundary through 2026-07-31.

## Frozen training contract

Fit exactly one final HGB model using the full accepted 278,168-row population with:

- `SimpleImputer(strategy=median, add_indicator=True, keep_empty_features=True)`;
- `HistGradientBoostingClassifier`;
- `learning_rate=0.05`;
- `max_iter=200`;
- `max_leaf_nodes=31`;
- `l2_regularization=1.0`;
- `random_state=42`;
- H10 target semantics `TP_FIRST=1`, `SL_FIRST=0`.

No CV search, hyperparameter tuning, early-stopping change, calibration, thresholding, ensemble, bagging, or feature selection is allowed.

## Required preflight

Before fitting, verify and persist:

- immutable panel SHA `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- canonical V3-B feature-order SHA `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- accepted O2 feature-order SHA above;
- exact common-support key hash;
- accepted Open panel/provenance hashes;
- accepted O2 runtime artifact manifest `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`;
- accepted robustness audit manifest `ba685239991ad820c45955c2116f56dd00a077b54a8d052c49adb2f97be438bd`;
- accepted minimality manifest `919e35bb8d2fe68588db331e3de25f6c2a490c2727aea9f68e1179c0bcbe5183`.

Fail closed on any mismatch.

## Required artifacts

Persist immutable/hashable artifacts for:

- final training row identities;
- final feature manifest/order/hash;
- training contract/model parameters;
- fitted preprocessing/model artifact;
- model SHA-256;
- environment/package versions required for reproducibility;
- input artifact hashes;
- final model manifest;
- runtime summary and artifact manifest.

The final manifest must state explicitly:

- `fresh_forward_outcomes_accessed=false`;
- `forward_outcome_access_marker_written=false`;
- `canonical_v3b_overwritten=false`;
- `independent_forward_validation_passed=false`;
- `execution_grade_promoted=false`.

## Forward scoring contract to freeze

Document, but do not execute forward validation:

- signal timestamp: after session-t close;
- geometry features may use session-t Open/High/Low only after that session is complete;
- same canonical V3-B eligibility/universe rules plus valid causal Open geometry availability;
- same feature definitions/order and model artifact hash;
- no historical/future outcome is required to produce a score;
- missing/invalid required Open geometry makes that ticker/session ineligible rather than synthetically filled.

Do not backfill or inspect any post-2026-07-31 outcome in this lane. A separate forward-validation spec will decide the first eligible O2 forward session after independent review of this final refit.

## Protected boundary

Not authorized:

- canonical V3-B replacement;
- fresh-forward outcome access or scoring evaluation;
- reuse/peek of the protected V3-B outcome vault;
- O3/new Open features/interactions/regime work;
- tuning or calibration;
- execution/PnL, Path Risk, probability/payoff/reliability, sizing, paper/live, or broker integration;
- provider/network calls or additional Open repair.

## Runtime decision

On successful completion emit exactly:

`O2_FULL_3_FINAL_REFIT_COMPLETE_PENDING_INDEPENDENT_REVIEW`

Run focused and full pytest, persist hashes/artifacts, write a dated runtime checkpoint and handoff, push fast-forward, then STOP for independent ChatGPT review.

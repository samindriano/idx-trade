# Expected Payoff V1 — Frozen Historical-Development Specification

Date: 2026-08-12 (Asia/Jakarta)

Branch: `research/idx-expected-payoff-v1`

Starting scientific anchor: `research/idx-expected-payoff-v0-feasibility` / `ecec6835eaee70f47a8a1c1b43fc2d14a4c34709`

Decision: `EXPECTED_PAYOFF_V1_HISTORICAL_EXPERIMENT_AUTHORIZED_FROZEN`

## 1. Purpose

Expected Payoff V0 established that the frozen O2 score contains historical-development information about the magnitude of a causal fixed-horizon payoff under the contract `signal close t -> entry Open t+1 -> exit Close t+10`.

V1 asks a narrower next question:

> Can one dedicated, preregistered payoff regressor estimate the conditional mean ATR-normalized gross H10 payoff out of sample, while preserving positive cross-sectional payoff ordering across the same frozen six historical folds?

V1 is a **separate secondary model**. It does not replace or retune O2 Alpha Ranking, Probability, Path Risk, Decision/Sizing, Portfolio, or Execution.

The only authorized candidate in this V1 is:

`PAYOFF_HGB_O2_FEATURES_V1`

No candidate search is authorized.

## 2. Protected boundaries

Hard constraints:

- historical-development evidence only;
- no read, join, derivation, inspection, or metric from any fresh-forward outcome after `2026-07-31`;
- do not touch or reinterpret the active O2 forward counter, score ledger, scheduler, outcome vault, O2.1 shadow, frontend, or forward capture;
- do not retrain, retune, or modify O2/V3-B/V2/O2.1/Probability/Path Risk;
- do not call any provider or network source;
- do not repair, synthesize, interpolate, or carry forward Open/Close;
- do not change the V0 entry, exit, horizon, ATR normalization, corporate-action handling, feature family, model family, hyperparameters, folds, metrics, or gates after observing V1 results;
- no H5/H20, alternate entry price, percent-payoff target, quantile model, feature mining, market-regime subgroup, clipping/winsorization, or residual rescue in this lane;
- V1 fits **one mean-payoff model only**. Distributional q25/q50/q75 modeling is explicitly deferred.

The old Stage-5 ranking holdout is not an independent validation set for this lane. V1 remains historical-development evidence and must not be described as fresh-forward proof.

## 3. Accepted parent identities

The implementation must fail closed unless it verifies the accepted parent lineage.

### O2 parent

- decision: `O2_SURVIVOR`;
- O2 artifact manifest SHA-256: `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`;
- O2 fold predictions SHA-256: `fe02c0c743e7bfc5a57b1c8e731c5685a4bff5f9854f910f88703b15a6ca8f0c`;
- O2 common-support row artifact SHA-256: `59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f`;
- O2 common-support stable key SHA-256: `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- O2 fold-definition artifact SHA-256: `f16ddd1640701b206cb10418ca9fa7736695fe8268ac5c38213ba22b1fe76046`;
- O2 feature-order SHA-256: `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`.

### Expected Payoff V0 parent

- frozen V0 spec decision: `EXPECTED_PAYOFF_V0_HISTORICAL_DIAGNOSTIC_AUTHORIZED_FROZEN`;
- accepted V0 verdict: `EXPECTED_PAYOFF_V0_FEASIBILITY_GO`;
- original V0 artifact manifest SHA-256: `c84170d5b438ad7481aa9a7985f377fbbd701ebfee80d720cd689d3bb7a49abd`;
- V0 resolved validation payoff key SHA-256: `f978ec6b81ddc72259e403e78698971f655721f94fbfdcc57f682c5cea3c4602`;
- accepted V0 parent rows: `140,679`;
- accepted V0 resolved validation rows: `140,595`;
- post-review diagnostic manifest SHA-256: `c750eac0c9b0784aa38bb45142a2b2ac4c835f13ad5d30af3309424e8ce8a121`.

The V1 runner must not assume row counts before identity checks. Counts are asserted only after verified parent loading.

## 4. Frozen feature contract

V1 uses **exactly the 36 O2 signal-time features**, in the accepted O2 order.

Canonical 33 V3-B features followed by exactly:

1. `open_position`;
2. `open_to_high`;
3. `open_to_low`.

The exact feature-order SHA-256 must remain:

`a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`.

No O2 score is appended as a feature. It is a deterministic downstream function of the same signal-time inputs and would create an unnecessary nested-score dependency for the training rows. O2 score is retained only as a validation comparator.

No additional raw ATR, ticker identity, sector identity, future data, date/year code, or hand-built regime feature may be added in V1.

## 5. Frozen payoff target

V1 uses the exact V0 causal price-payoff contract.

For signal session `t`:

- entry = accepted Regular-Market `Open_(t+1)`;
- exit = preserved raw `Close_(t+10)`;
- `ATR14_t = Close_t * atr14_over_close_t` from the verified canonical signal-time feature source;
- target:

`payoff_atr_gross = (Close_(t+10) - Open_(t+1)) / ATR14_t`.

Secondary percentage payoff is retained for diagnostics only:

`payoff_pct_gross = Close_(t+10) / Open_(t+1) - 1`.

No fees, taxes, spread, slippage, partial fill, or market impact are included. The word `gross` remains mandatory.

Corporate-action/raw-price integrity and accepted Open provenance use the exact V0 fail-closed rules. A price-scale-changing corporate-action crossing remains excluded unless an already-accepted canonical adjustment existed before this V1 was frozen. No new adjustment may be invented here.

## 6. Frozen fold and population contract

Use the exact six accepted O2 expanding folds and exact O2 common-support universe.

### Validation rows

Validation is **exactly the accepted V0 resolved payoff rows for each corresponding O2 validation fold**. Therefore V1 and O2 comparator metrics are paired on the same validation ticker/session/payoff keys.

The validation stable key must equal the accepted V0 resolved payoff key:

`f978ec6b81ddc72259e403e78698971f655721f94fbfdcc57f682c5cea3c4602`.

Do not drop a validation row because the V1 prediction is inconvenient. If the frozen model cannot emit a finite prediction for an accepted V0 validation row, the fold is data/model blocked.

### Training rows

For each fold, training starts from the exact O2 common-support rows assigned to that fold's accepted training window.

Resolve the V1 payoff target using the exact V0 contract. Training rows are usable only when:

- all 36 O2 features satisfy the already-accepted O2 common-support contract;
- the fixed payoff target is resolved under V0 provenance/tradability/corporate-action rules;
- `t+10` is fully historical and matured before the fold validation begins under the accepted purge contract;
- no observation after the fold's allowed training boundary is used in feature preprocessing, target construction, baseline estimation, or model fitting.

The accepted O2 20-session purge remains controlling and is more than the 10-session payoff horizon. Do not shorten it.

Rows excluded from training target resolution remain in a training-coverage ledger with one explicit reason.

## 7. Frozen model candidate

Candidate:

`PAYOFF_HGB_O2_FEATURES_V1`

Pipeline:

1. numeric 36-feature input in the frozen O2 order;
2. `SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)` fit on the fold training rows only;
3. `HistGradientBoostingRegressor` with exactly:
   - `loss="squared_error"`;
   - `learning_rate=0.05`;
   - `max_iter=200`;
   - `max_leaf_nodes=31`;
   - `l2_regularization=1.0`;
   - `early_stopping=False`;
   - `random_state=42`.

All unspecified estimator parameters remain the installed library defaults and must be persisted in the model contract artifact.

No hyperparameter search, early-stopping search, target transformation, sample weighting, clipping, winsorization, ticker fixed effect, or ensemble is allowed.

Rationale: V1 tests one direct nonlinear conditional-mean payoff model with a model class already familiar in the ranking stack while changing the optimization target from binary alpha outcome to continuous gross payoff magnitude.

## 8. Frozen baselines and comparators

### 8.1 Numeric calibration baseline — `TRAIN_MEAN_PAYOFF`

Within each fold, compute the mean `payoff_atr_gross` on resolved **training rows only**.

Predict this constant for every validation row.

This baseline is the primary comparator for numerical expected-payoff accuracy. No validation outcome may influence it.

### 8.2 Ranking comparator — frozen O2 score

Use the exact accepted O2 score already attached to the V0 validation rows. Do not retrain or rescore O2.

The O2 score comparator is contextual: V1 is not required to become a better Alpha ranker than O2. It is used to show whether the dedicated payoff model preserves or changes cross-sectional ordering.

## 9. Frozen metrics

Evaluation unit for cross-sectional metrics remains the **signal session**.

### 9.1 Primary calibration metric

For each fold on the exact validation rows:

- `MSE_V1` on `payoff_atr_gross`;
- `MSE_TRAIN_MEAN` from the constant training-mean baseline;
- `MSE_SKILL = 1 - MSE_V1 / MSE_TRAIN_MEAN`.

Also persist RMSE and MAE for V1 and baseline, but MSE skill is gating.

A positive `MSE_SKILL` means V1 improves squared-error conditional-mean estimation versus predicting one historical mean for all validation rows.

### 9.2 Session payoff IC

For every validation signal session with at least 30 rows and non-constant prediction/payoff, compute Spearman correlation between:

- V1 predicted `expected_payoff_atr_gross`;
- realized `payoff_atr_gross`.

Persist mean/median/std by fold.

Compute the same session IC using frozen O2 score for paired contextual comparison.

### 9.3 Predicted-payoff D10-D1 spread

Within each validation session, deterministic stable-sort by `(V1 predicted payoff, ticker)`, split into ten approximately equal-count ordinal bins, and compute:

`mean(realized payoff in D10) - mean(realized payoff in D1)`.

Persist fold mean and median spread.

### 9.4 Calibration and monotonicity diagnostics — non-gating

Persist by fold and pooled historical-development diagnostics:

- predicted-payoff decile mean predicted versus mean realized ATR payoff;
- calibration intercept and slope from decile means where finite;
- decile-index versus realized mean payoff Spearman;
- prediction mean, std, q01, q05, q25, q50, q75, q95, q99;
- realized-payoff mean/std and prediction bias;
- same broad diagnostics for percentage payoff as secondary only;
- V1 minus O2 session-IC paired differences as contextual, non-gating evidence.

Do not create post-result calibration transforms in V1.

## 10. Frozen data-readiness gate

`EXPECTED_PAYOFF_V1_DATA_READY` requires all of:

1. all parent/model/data/fold/feature hashes match the accepted identities;
2. validation rows are exactly the accepted V0 resolved payoff keys, with 100% finite V1 predictions;
3. each fold training target resolves for at least 90% of otherwise eligible O2 common-support training rows;
4. every fold has at least 80 metric-eligible validation sessions with at least 30 rows;
5. preprocessing statistics are fit on training rows only;
6. no post-`2026-07-31` outcome/data access;
7. no provider calls, target repair, O2 rescore/retrain, or fresh-forward marker/runtime access.

If any condition fails, verdict is `EXPECTED_PAYOFF_V1_DATA_BLOCKED`. Do not weaken the gate.

## 11. Frozen survivor gate

If and only if data readiness passes, V1 receives:

`EXPECTED_PAYOFF_V1_SURVIVOR`

only when **all** conditions hold:

### Conditional-mean accuracy

1. median across six fold `MSE_SKILL` values is strictly `> 0`;
2. at least `4/6` folds have `MSE_SKILL > 0`.

### Cross-sectional payoff ordering

3. median across the six fold-median session IC values is strictly `> 0`;
4. q25 across the six fold-median session IC values is strictly `> 0`;
5. at least `4/6` folds have positive median session IC.

### Economic spread guardrail

6. median across six fold-mean V1 D10-D1 ATR payoff spreads is strictly `> 0`;
7. at least `4/6` folds have positive mean V1 D10-D1 ATR payoff spread.

Otherwise, after data readiness passes, verdict is:

`EXPECTED_PAYOFF_V1_NO_SURVIVOR`.

There is deliberately no minimum absolute R threshold, p-value rescue, alternate loss, target clipping, quantile rescue, feature subset search, alternate model, or subgroup rescue after the result.

O2-relative paired improvement is **not** part of the survivor gate because O2 and Expected Payoff have different jobs: O2 ranks binary opportunity; V1 estimates conditional payoff magnitude. O2-relative metrics remain contextual only.

## 12. Required artifacts

Persist and hash-manifest at minimum:

- `preflight_contract.json`;
- `parent_identity.json`;
- `feature_manifest.json`;
- `fold_definitions.json` or exact verified parent reference;
- `training_payoff_coverage.csv`;
- `training_exclusion_reasons.csv`;
- `fold_training_summary.csv`;
- `validation_predictions.parquet` with exact V0 validation keys, frozen O2 score, V1 prediction, realized ATR payoff, and secondary percent payoff;
- `session_metrics.csv`;
- `fold_metrics.csv`;
- `predicted_payoff_decile_summary.csv`;
- `calibration_diagnostics.csv`;
- `aggregate_metrics.json`;
- `survivor_decision.json`;
- `artifact_manifest.json`.

Persist stable SHA-256 identities for:

- training key set per fold;
- exact validation key set;
- feature order;
- model contract;
- each fitted fold model artifact if serialized;
- all required output artifacts.

Protected flags must explicitly state:

- `fresh_forward_outcomes_accessed=false`;
- `forward_outcome_access_marker_written=false`;
- `provider_calls=false`;
- `o2_model_modified=false`;
- `o2_rescored=false`;
- `payoff_v1_hyperparameter_search=false`;
- `payoff_v1_candidate_count=1`.

## 13. Required tests

At minimum test:

- exact 36-feature order/hash and rejection of any extra/missing/reordered feature;
- validation keys exactly equal the accepted V0 resolved keys;
- training target uses the exact V0 `t+1 Open -> t+10 Close` ATR-normalized contract;
- training payoff cannot cross the validation/purge boundary;
- imputer/model fit receives training rows only;
- constant baseline uses training target mean only;
- MSE skill formula and zero-baseline-error fail-closed handling;
- deterministic session deciles under prediction ties;
- survivor gate boundary cases, including exactly 4/6 positive folds;
- finite prediction requirement on every accepted validation row;
- corporate-action/Open-provenance exclusions remain fail-closed;
- no O2 rescore/retrain path;
- no fresh-forward outcome/runtime/marker/provider path.

Run focused tests and the full repository pytest suite.

## 14. One-shot stop rule

Run the frozen six-fold V1 experiment once after implementation.

If `EXPECTED_PAYOFF_V1_DATA_BLOCKED`:

- stop for independent review;
- do not lower data-readiness requirements.

If `EXPECTED_PAYOFF_V1_NO_SURVIVOR`:

- close this exact model hypothesis;
- do not rescue with Ridge/XGBoost/LightGBM, target clipping, quantile loss, extra features, O2-score feature, H5/H20, alternate normalization, or subgroup filtering in this lane.

If `EXPECTED_PAYOFF_V1_SURVIVOR`:

- persist artifacts and stop for independent ChatGPT review;
- do not automatically final-refit, add quantile models, expose it in frontend, combine it with Probability/Path Risk, or start sizing;
- any final-refit/shadow-forward or distributional-payoff continuation requires a separate frozen checkpoint.

This V1 specification is frozen before any V1 model result is observed.

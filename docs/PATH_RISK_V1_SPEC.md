# Path Risk V1 — Adverse Excursion Quantile Specification

Date: 2026-08-10 (Asia/Jakarta)
Status: **FROZEN PRE-OUTCOME SPEC — SEPARATE RISK LANE, NOT RANKER RETUNING**

## 1. Purpose

The alpha-ranking search is closed. The frozen final ranker is:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

Path Risk V1 asks a different question:

> Given the same causal information available at the signal close, can a separate model estimate upper-tail adverse path excursion before the setup resolves, without replacing, retuning, filtering, or re-ranking the frozen opportunity model?

This is a secondary risk-estimation lane. It is not a new alpha candidate and does not change the permanent historical ranking-candidate count of `17`.

No Path Risk result may be used to modify the 33-feature ranker, V3/V4 architecture, target, fresh-forward ranking verdict, or historical candidate selection.

## 2. Frozen hypothesis

Hypothesis ID:

`PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1`

There is exactly one learned challenger in V1:

`PATH-RISK-A-Q75-HGB-001`

Comparator:

`TRAIN-Q75-CONSTANT-BASELINE`

No second model family, alternate quantile, alternate target, lookback grid, feature ablation, threshold search, blending, or rescue candidate exists in this experiment.

## 3. Frozen target

The target is **pre-resolution adverse excursion in stop-distance units** over the existing H10 barrier setup.

Reuse the existing frozen barrier semantics exactly:

- signal reference = signal-date close;
- ATR = causal ATR14 at the signal date;
- stop distance = `1.0 * ATR14`;
- stop level = reference close minus one stop distance;
- target level = reference close plus `1.5 * stop distance`;
- horizon = 10 official sessions;
- no Open dependency.

For a signal at official session `t`, define the target path end `tau` as:

- the first barrier-touch date when the frozen H10 label has a first barrier date; or
- `t+10` when no barrier is touched within H10.

Use future lows from `t+1` through `tau`, inclusive.

Define:

```text
adverse_excursion_r = max(0, (signal_reference_close - min_future_low_to_tau) / stop_distance)
```

The target is **not capped at 1.0**. A stop-touch bar may overshoot the stop and therefore produce `adverse_excursion_r > 1`. This is path-severity geometry, not an execution-fill or realized-loss claim.

Target-eligible statuses are the existing path-complete, valid-barrier outcomes:

- `TP_FIRST`;
- `SL_FIRST`;
- `AMBIGUOUS_SAME_BAR`;
- `NO_BARRIER_HIT`.

Exclude:

- `UNRESOLVED_PATH`;
- `UNRESOLVED_HORIZON_END`;
- `INVALID_BARRIER`;
- any row without complete official H10 evidence.

Mechanical invariants:

- target finite and `>= 0`;
- `SL_FIRST` and `AMBIGUOUS_SAME_BAR` must have target `>= 1` within numerical tolerance;
- `TP_FIRST` and `NO_BARRIER_HIT` must have target `< 1` within numerical tolerance;
- target construction must preserve exact frozen H10 `label_status`, `first_barrier_date`, signal reference, ATR, stop level, and target level from the immutable H10 label artifact; disagreement is a hard stop.

The immutable H10 label artifact identity is:

`a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`

Target construction may not inspect post-2026-07-31 data.

## 4. Frozen information set

The learned risk model uses exactly the already-frozen 33 causal V3-B feature columns:

- exact V2 25-feature prefix;
- exact eight Structure-Lite columns.

Feature-order identity:

`100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`

Do **not** use:

- binary target;
- H10 status;
- MFE/MAE outcome columns;
- first-barrier date;
- frozen ranker score/probability as an input;
- ticker ID/dummies;
- future state;
- current-survivor shortcuts;
- Open;
- V4 failed features;
- sector/fundamental/flow data.

The Path Risk model therefore sees the same causal market/setup information, but learns a different target.

## 5. Outcome-blind feature-frame contract

The feature cache must be built from the immutable signal-research sources:

- signal panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

For discovery, physically materialize only signal sessions through `984`.

Build:

1. exact existing causal baseline features on the full ACTIVE-only signal panel;
2. exact existing V2 cross-sectional/market features using the full same-date causal primary-liquid universe;
3. exact frozen Structure-Lite features through session `984`;
4. one-to-one join on `(ticker,date)`;
5. retain the full `universe_primary_liquid == true` feature population, **not only rows whose future binary TP/SL label resolves**.

This rule prevents post-outcome selection bias in the risk layer.

The feature-cache prepare/audit phase must not load H10 labels or any outcome column.

Hard feature-cache checks:

- max signal session exactly `<=984`;
- no session `985+` physically materialized in the discovery cache;
- no outcome/target columns present;
- no duplicate `(ticker,date)`;
- exact 33-feature order/hash;
- no infinity in any model feature;
- missing values preserved for training-only imputation;
- V2 market-context features built from the full causal primary-liquid same-date universe;
- deterministic source/cache/manifest hashes.

## 6. Frozen model

`PATH-RISK-A-Q75-HGB-001` uses:

- `ColumnTransformer` selecting the exact 33 columns;
- median `SimpleImputer`;
- `add_indicator=True`;
- `keep_empty_features=True`;
- no scaler;
- `HistGradientBoostingRegressor`;
- `loss="quantile"`;
- `quantile=0.75`;
- `learning_rate=0.05`;
- `max_iter=200`;
- `max_leaf_nodes=31`;
- `l2_regularization=1.0`;
- `random_state=42`.

Model output is a **conditional 75th-percentile adverse-excursion estimate in R units**. It is not a probability and is not a position-sizing instruction.

The constant comparator predicts, for every validation row, the training fold's empirical 75th percentile of the target using NumPy/Pandas linear quantile semantics. Validation outcomes must not affect the baseline constant.

## 7. Historical-development folds

Reuse the exact chronological V2 fold boundaries because they already carry a conservative 20-session purge around an H10 future target.

Discovery consumes only:

- F1: train `1..504`, gap `505..524`, validation `525..624`;
- F2: train `1..624`, gap `625..644`, validation `645..744`;
- F3: train `1..744`, gap `745..764`, validation `765..864`;
- F4: train `1..864`, gap `865..884`, validation `885..984`.

F5/F6 remain sealed from Path Risk until a separate one-shot late-development authorization after a discovery PASS.

The fact that F5/F6 were previously seen for ranking does not make them independent market-time validation for Path Risk. If later used, they are only Path-Risk late-development confirmation.

## 8. Frozen discovery metrics

Primary proper scoring metric:

- 0.75 pinball loss, lower is better.

Report per fold for model and constant baseline:

- pinball loss;
- relative pinball improvement:

```text
(baseline_pinball - model_pinball) / baseline_pinball
```

Also report diagnostics:

- MAE;
- Spearman correlation between predicted risk and realized adverse excursion;
- empirical quantile coverage `P(y <= qhat)`;
- absolute coverage error versus `0.75`;
- within-date predicted-risk quintiles;
- realized mean adverse excursion in lowest and highest predicted-risk quintiles;
- Q5-Q1 realized adverse-excursion spread;
- rate `adverse_excursion_r >= 1` in lowest and highest predicted-risk quintiles;
- validation rows, dates, tickers, target-status composition;
- prediction finite rate and unique-prediction count.

The stop-touch-rate diagnostics are descriptive only. This experiment does not produce calibrated stop probabilities.

## 9. Frozen F1-F4 discovery gate

The candidate survives discovery only if all are true:

1. all required metrics and predictions are finite;
2. target/data/provenance gates pass;
3. relative pinball improvement is `>=0` on at least `3/4` folds;
4. median relative pinball improvement is `>= +0.02`;
5. q25 relative pinball improvement is `>= 0`;
6. worst relative pinball improvement is `>= -0.01`;
7. Spearman correlation is positive on at least `3/4` folds;
8. median Spearman correlation is `>= +0.10`;
9. realized Q5-Q1 adverse-excursion spread is positive on at least `3/4` folds;
10. median realized Q5-Q1 spread is `>= +0.10 R`.

Empirical q75 coverage is reported but is not a promotion gate in V1 because pinball loss is the proper scoring objective and the historical distribution may shift between folds.

If every condition passes:

`PATH_RISK_A_DISCOVERY_PASS`

Otherwise:

`PATH_RISK_A_DISCOVERY_FAIL_CLOSE`

There is no MIXED state, target rewrite, quantile change, model swap, feature pruning, fold exclusion, or threshold relaxation after results are viewed.

## 10. Candidate accounting

Path Risk uses a separate ledger from ranking alpha research.

- `PR-001`: `PATH-RISK-A-Q75-HGB-001`.

The constant baseline is a comparator, not a learned candidate ordinal.

A discovery run permanently marks PR-001 viewed whether it passes or fails.

The ranking denominator remains `17` and is not incremented by Path Risk.

## 11. What a PASS means

A PASS means only:

> The frozen 33-feature causal setup representation contains robust historical-development information about upper-quartile pre-resolution adverse excursion beyond an unconditional training-quantile baseline.

It does **not** mean:

- the ranker should be changed;
- high predicted risk should automatically veto a trade;
- realized PnL improves;
- a stop should be moved;
- the risk estimate is calibrated probability;
- Kelly sizing is valid;
- live/paper readiness is established.

Any future rule combining opportunity rank and Path Risk requires a separate preregistered integration study after Path Risk itself is confirmed.

## 12. Fresh-forward protection

Path Risk V1 must not access, summarize, or indirectly consume the reserved post-2026-07-31 fresh-forward ranking outcome block.

Do not write `FORWARD_OUTCOME_ACCESS_STARTED`.

Path Risk historical development is limited to the already-consumed historical research period and must not alter the exact first 100-session independent ranking verdict contract.

## 13. Immediate implementation sequence

The next authorized engineering task is **implementation + outcome-blind discovery feature-cache preparation/audit only**.

That task may:

- implement target-builder code and tests using synthetic/historical bounded fixtures without running the real target builder;
- implement the q75 model/runner/gates and tests;
- build the real outcome-blind 33-feature primary-liquid discovery cache through session `984`;
- audit feature coverage/constancy/redundancy mechanically;
- freeze/hash the feature cache and manifest.

It must stop before loading the real H10 label artifact or calculating any real Path Risk target/performance metric.

A separate ChatGPT review is required before PR-001 F1-F4 outcome access.

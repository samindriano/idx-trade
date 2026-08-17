# Ranking V4-3 — preregistration locked before target/model outcomes

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-3-preregistration-v1`
Scientific parent: `review/idx-v4-target-support-census-acceptance-v1@34fc78fa6234cdcc5093e8c4ea36a444b358cec7`
Status: `V4_3_SCIENTIFIC_CONFIG_LOCKED_PRIMARY_LIQUID_SUPPORT_AND_FOLD_BYTES_PENDING`

## Boundary

This checkpoint freezes the remaining scientific degrees of freedom before any V4 historical return, target rank, fitted model, prediction, IC, Top-30 result, or raw-return performance diagnostic is inspected.

No V4 target or model outcome was materialized while selecting this contract.

V4-0, V4-1, and V4-2 remain controlling and unchanged. Their checkpoint blob identities are respectively:

- V4-0: `7d55c2b11db50ca6a589daa74627c5a963954b42`;
- V4-1: `afc4d171cf4f735839782d31256c8894283701f4`;
- V4-2: `48ebfc2bd37ced730f2257d49b708f4a2e1d3963`.

The accepted remediated broad target-support census remains valid evidence that 6x100 is technically plausible: H5/H10/consensus had 910/891/815 eligible sessions on the full ACTIVE signal-research population. It is not reused as the final fold identity because V4-3 now freezes the narrower scoring universe below.

## Provenance closure

The previously missing `docs/SIGNAL_RESEARCH_HLCV_CONTRACT.md` was recovered from the PIT-safe historical lineage and restored byte-for-byte with no semantic edit.

- restored Git blob SHA-1: `4d034e628838f56a0c88b3f23e249fae51a803ac`;
- SHA-256 of exact bytes: `ffff2d21b275744a3a2b74c2f7d32be7b589f3c46cf9950c5ff45c48e5bffd73`;
- historical source commit: `765bdba170eba68d3beab28dae30bd7e694743f8`.

This closes the missing-contract byte-identity warning for downstream V4-3 work without changing the signal-research semantics.

## Frozen decision universe

Initial V4 uses `V4_PRIMARY_LIQUID_CAUSAL_V1`.

A signal row must already satisfy the signal-research HLCV contract and the causal primary-liquidity rule:

- trailing window: 60 **official exchange sessions**, including signal session `t`;
- at least 20 finite observed ACTIVE `regular_market_value` observations inside that official-session window;
- median `regular_market_value` >= IDR 1,000,000,000;
- no Top-100/Top-300 rank filter;
- all membership is determined at EOD `t`, never from future target state.

This is the exact historical Clean-V2 universe rule from `research_features.py` at commit `46a5a2e9eaadb6111d59214633511eb11d21ab9e`, blob `05102f47031b61e6a71032244167cb7f36a981f5`.

The rule is retained as the **initial universe control**, not claimed to be historically optimal. Its threshold/lookback/minimum-observation parameters may not be changed after V4 target access.

Because V4-2's >=90% observability gate applies to the original **scored** decision population, exact support must now be refreshed once on this primary-liquid universe. The broad 981,940-row census cannot substitute for that narrower denominator.

## Frozen target-rank convention

V4-1's H5/H10 raw-return definitions remain unchanged.

Within each admitted decision date, each horizon target uses average-tie rank normalized exactly to `[0,1]`:

`target_rank = (average_rank_ascending - 1) / (n - 1)` for `n > 1`.

For `n == 1`, rank is `0.5`.

H5 ranks are computed over defensibly H5-observable rows; H10 ranks independently over defensibly H10-observable rows. Realized consensus averages the two ranks only where both exist. Negative or zero returns remain valid outcomes.

Predicted raw scores use the same within-date normalized-rank convention, but the ranking population is the full primary-liquid decision-time scoring universe **before future target observability is known**.

## Shared validation calendar and folds

H5, H10, and consensus use one shared validation-date calendar: the primary-liquid **consensus-eligible** sequence.

If the outcome-blind refreshed support census produces fewer than 600 consensus-eligible dates, V4-3 is `BLOCKED`; the fold design is not changed.

If at least 600 exist:

1. sort consensus-eligible official sessions chronologically;
2. select the **last 600** eligible sessions;
3. split them chronologically into six non-overlapping folds of 100 dates each;
4. no fold boundary is chosen using target magnitude or model performance.

The tail-600 rule leaves the largest available pre-validation history while keeping the validation period as recent as possible under the already frozen historical-development cutoff.

### Purge

Purge uses the **official exchange-session index**, not gaps in the filtered eligible sequence.

For a validation fold whose first official session index is `s`, training signal sessions `s-10 ... s-1` are excluded. Therefore the latest permitted training signal index is `s-11`.

This prevents an H10 training label from reaching into the validation information window.

### Training-date admission

- Alpha-H5 trains on prior H5-eligible primary-liquid dates before the purge boundary.
- Alpha-H10 trains on prior H10-eligible primary-liquid dates before the purge boundary.
- within an admitted training date, only rows with a defensible target for that head enter supervised fitting;
- control and challenger use exactly the same row identities for a given head/fold;
- feature missingness never drops a row.

For a 100-date validation fold, a fold-level primary metric is promotion-eligible only with at least 90 admitted daily observations for that metric. All six fold summaries are required for promotion.

## Frozen training weighting

The pooled regression loss is date-balanced.

For training row `i` on date `d`:

`w_i = N_train_rows / (N_train_dates * n_target_rows_on_date_d)`.

Thus every training date contributes equal total weight and mean sample weight remains 1. This aligns the learner with V4-2's date-centric product/evidence unit without changing regularization scale merely because dates have different universe sizes.

## Frozen V4 Control

Control ID: `V4_CONTROL_CONTEXT25_HGBR`.

It uses exactly the Clean-V2 25-column contextual representation:

- 10 within-date cross-sectional ranks;
- 9 continuous market-context fields;
- 6 stock-minus-market fields.

Exact source semantics are pinned to `research_v2_features.py` at commit `46a5a2e9eaadb6111d59214633511eb11d21ab9e`, blob `ccbcc7553a5aeb8ede9b32a8dd12ec7a45cb7290`.

This inherits only the initial representation/control information class. It does **not** inherit the old binary target, old fitted model, old PR/ROC magnitude, or a final-alpha claim.

## Frozen initial challenger

Challenger ID: `V4_CHALLENGER_SESSION_GEOMETRY3`.

This is the **only** initial challenger and adds exactly three non-redundant completed-session EOD-t geometry features:

1. `session_open_position_range = (Open_t - Low_t)/(High_t-Low_t)`;
2. `session_body_signed_range = (Close_t-Open_t)/(High_t-Low_t)`;
3. `session_log_high_low_range = log(High_t/Low_t)`.

For the two Open-dependent fields, Open must be finite, positive, and inside the same-day Low-High envelope. No synthetic Open is allowed. If `High == Low > 0`, the first two features are undefined/NaN and log-range is 0.

The block was chosen outcome-blind because completed-session geometry remains a retained conditional information hypothesis, accepted historical Open coverage now exists, and it avoids the unresolved long-window price-continuity issue of the old Structure-Lite implementation.

**Structure-Lite is not declared failed.** It is parked for a separate preregistered challenger after long-window corporate-action/price-continuity semantics are explicitly resolved. It may not replace Geometry3 after V4 results are seen.

No Geometry3 subset or alternate wick/body coordinate may be tested as a V4 rescue.

## Frozen preprocessing

Control block:

- training-only median imputation;
- missing indicators enabled;
- empty features retained;
- no scaling.

Geometry3 block:

- training-only median imputation;
- **no missingness indicator**;
- empty features retained;
- no scaling.

The geometry missingness indicator is deliberately excluded because historical Open missingness is partly a provider/provenance artifact and must not itself become an alpha signal. Geometry availability remains a mandatory diagnostic only.

## Frozen learner

Both heads and both control/challenger use the same learner family:

`sklearn.ensemble.HistGradientBoostingRegressor(loss="squared_error")`.

Frozen effective configuration:

- learning rate `0.05`;
- max iterations `200`;
- max leaf nodes `31`;
- max depth `None`;
- minimum samples per leaf `20`;
- L2 regularization `1.0`;
- max bins `255`;
- categorical features `None`;
- warm start `False`;
- early stopping `False`;
- random seed `42`.

No hyperparameter search, validation-driven early stopping, calibration, clipping, or learner-family search is permitted.

`main` does not currently declare scikit-learn as a project dependency. Therefore no fit is authorized until the exact local Python/numpy/pandas/scikit-learn versions are recorded and hash-pinned **before first target/model execution**, and the estimator signature/effective parameters are verified. That environment choice is an engineering prerequisite, not a post-result tuning degree of freedom.

## Frozen bootstrap implementation

V4-2's 10-session / 2,000-rep / seed-42 / 95% moving-block bootstrap is concretized as fold-stratified MBB:

- inside each 100-date fold, possible non-circular 10-date block starts are `0..90`;
- sample 10 such blocks with replacement to reconstruct 100 dates for that fold;
- repeat independently for each of six folds and concatenate to 600 resampled dates;
- compute the requested statistic;
- repeat 2,000 times;
- report the 2.5% and 97.5% percentile interval.

Bootstrap blocks never cross fitted-model fold boundaries.

## Frozen absolute viability gates

These thresholds are **outcome-blind research priors**, not literature claims of universally optimal IC.

Every gate is required.

### H5 and H10 individually

For each head:

- median across six fold mean daily IC >= `0.015`;
- q25 across six fold mean daily IC >= `0.000`;
- at least `4/6` folds have positive mean daily IC;
- median fold Top-30 mean realized target percentile >= `0.51`;
- median fold Top-30 minus Bottom-30 realized percentile spread >= `0.02`.

### Consensus

- median fold mean daily IC >= `0.025`;
- q25 fold mean daily IC >= `0.010`;
- at least `5/6` folds have positive mean daily IC;
- 95% moving-block-bootstrap lower bound for mean daily IC > `0`;
- median fold Top-30 mean realized consensus percentile >= `0.52`;
- median fold Top-30 minus Bottom-30 spread >= `0.04`;
- q25 fold Top-30 minus Bottom-30 spread >= `0`.

Passing means only `historical-development viability`. Fresh prospective confirmation remains mandatory.

## Frozen challenger-vs-control promotion gates

All comparisons are paired on exact common validation support. Geometry missingness may not drop rows. Top-30 daily deltas are admitted only when both models' own original Top-30 metrics pass the frozen 27/30 observability rule.

Geometry3 may be promoted only if **it also passes every absolute viability gate above** and all of the following incremental gates:

- consensus median fold mean IC delta >= `+0.005`;
- consensus q25 fold mean IC delta >= `0`;
- consensus IC delta positive in at least `4/6` folds;
- paired consensus mean-daily-IC-delta bootstrap 95% lower bound > `0`;
- H5 median fold mean IC delta >= `0`;
- H10 median fold mean IC delta >= `0`;
- H5 q25 fold mean IC delta >= `-0.005`;
- H10 q25 fold mean IC delta >= `-0.005`;
- consensus median fold Top-30 realized-percentile delta >= `+0.005`;
- consensus median fold Top-30-minus-Bottom-30 spread delta >= `+0.01`.

All gates are conjunctive. There is no metric substitution after results.

## Decision logic

- control passes, challenger fails promotion -> `CONTROL_RETAINED`;
- challenger passes absolute + all incremental gates -> `CHALLENGER_PROMOTED_FOR_FRESH_PROSPECTIVE_CONFIRMATION`;
- control fails and challenger also fails -> `V4_GENERATION_NO_SURVIVOR`;
- control fails but the already-preregistered challenger passes absolute + incremental gates -> challenger may survive; this is not a rescue because both were frozen before outcomes.

Frozen Clean V2 under the old target is contextual historical evidence only. A final old refit trained through a V4 validation date is prohibited as a benchmark on that date. Only genuinely pre-existing out-of-sample old-model scores may be shown diagnostically, and legacy performance cannot override V4 gates.

## Mandatory raw-return diagnostics

V4-2 raw-return diagnostics remain mandatory and unchanged, but no raw-return/PnL/Sharpe/Kelly threshold is added to promotion. They are interpretation diagnostics, not an alternate rescue objective.

## Machine-readable contract and implementation

Frozen config:

`config/ranking_v4_3_preregistration.json`

Current Git blob SHA-1: `57cc72ee68a9484b6bfe3843da17caadd5373908`.

Outcome-blind helpers:

`src/idx_trade/ranking_v4_3_preregistration.py`

Outcome-blind exact-universe support/fold materializer:

`scripts/run_v4_3_primary_liquid_support.py`

Focused invariant tests:

`tests/test_ranking_v4_3_preregistration.py`

## Remaining pre-fit hard gate

One local-data step remains because the authoritative panel/Open artifacts live outside Git on the user's Windows machine.

The materializer must run exactly once on the pinned inputs and either:

- produce >=600 primary-liquid consensus-eligible sessions, exact last-600 fold identities, and purge boundaries, all hash-pinned; or
- return `V4_3_PRIMARY_LIQUID_SUPPORT_BLOCKED_6X100_INFEASIBLE`.

If blocked, do not inspect target magnitudes and do not change this preregistration as a result-driven rescue.

The resulting small eligible/fold/manifest artifacts belong in Git under the existing artifact-governance policy; raw panels remain external.

After that, pin the exact installed runtime dependency versions. Only then may a separately reviewed target-materialization/model runner be authorized.

## Prohibited after any V4 target access

No changes to target horizons/weights, universe threshold, fold selection, purge, Top30, rank convention, training weighting, learner/hyperparameters, imputation, Geometry3 definition/subset, challenger family, or numerical gates.

A clean weak result is allowed. V4 is not to be rescued.

Verdict:

`V4_3_SCIENTIFIC_CONFIG_LOCKED_PRIMARY_LIQUID_SUPPORT_AND_FOLD_BYTES_PENDING`

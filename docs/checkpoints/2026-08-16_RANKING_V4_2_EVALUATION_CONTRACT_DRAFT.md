# Ranking V4-2 — Evaluation and Promotion Contract Draft

Date: 2026-08-16 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-2-evaluation-contract-v1`
Parent V4-1 lock: `199d770520edcd4a7b4537c75d5edaba2b0aa349`
Status: `V4_2_EVALUATION_CONTRACT_DRAFT_FOR_REVIEW_NO_MODEL_OR_OUTCOME_RUN`

## Scope

Outcome-blind evaluator design only. No V4 labels are materialized, no model is fit, no historical V4 performance is computed, and no protected/fresh-forward outcome is accessed.

V4-0 and V4-1 remain controlling:

- Alpha V4 is opportunity ranking only.
- Two separately fitted targets exist: H5 and H10 within-date forward-return percentile ranks.
- Product consensus is the frozen 50/50 average of predicted H5 and H10 percentiles.
- H5/H10 are forecast horizons, not mandatory exits.

## Core evaluation principle

The primary unit of evidence is the **decision date**, because the product makes one cross-sectional ranking decision per EOD session.

A date with 800 observable stocks must not automatically carry twice the scientific weight of a date with 400 observable stocks merely because it contains more rows.

Therefore V4 evaluation is date-centric first and pooled-row metrics, if reported, are diagnostic only.

## Validation structure recommendation

Initial historical-development protocol:

- chronological expanding-window validation;
- six validation folds;
- each validation fold spans 100 consecutive eligible signal sessions where feasible;
- training uses only sessions strictly before validation;
- purge is governed by the longest frozen target, H10;
- at least 10 signal sessions immediately before each validation block are excluded from training so no training label reaches into the validation information window;
- no random split;
- no future-data interpolation;
- no post-result fold-boundary changes.

Exact calendar/session identities must be materialized from the canonical session index before any outcome computation.

## Population and observability

For every signal date `t`, the alpha scoring population is frozen from EOD-t information.

Future target observability is tracked separately. A row may become:

- `TARGET_H5_AVAILABLE`
- `TARGET_H10_AVAILABLE`
- `TARGET_BOTH_AVAILABLE`
- `MARKET_ENTRY_UNAVAILABLE`
- `TARGET_DATA_UNOBSERVABLE`
- `PRICE_CONTINUITY_UNRESOLVED`
- another separately enumerated fail-closed state if required by implementation.

A poor, negative, zero, or sideways realized return is never a reason to drop a row.

Any challenger-versus-control comparison must use exact common support for the metric being compared.

## Primary horizon metrics

Evaluate H5 and H10 independently.

For each decision date and horizon:

### 1. Daily cross-sectional Spearman IC

Spearman rank correlation between model score and the realized within-date target percentile.

Interpretation:

- positive = stocks scored higher tended to finish higher in the realized cross-sectional ordering;
- zero = no rank association;
- negative = ordering tends to be wrong.

Report per fold:

- mean daily IC;
- median daily IC;
- fraction of positive-IC dates;
- dispersion / lower-tail diagnostics.

Across folds, the primary summary should emphasize the median and lower quartile rather than only the grand pooled average.

### 2. Top-30 realized target percentile

For each decision date, select the 30 highest-scored observable stocks (or all stocks if fewer than 30 are observable) and compute the mean realized target percentile of those names.

This directly evaluates the product question: did the model move genuinely strong future performers into the practical shortlist?

A random/uninformed ranking has an expected realized percentile near the center of the cross-section. Higher is better.

### 3. Top-30 versus bottom-30 realized target spread

For each date:

`mean(realized_target_percentile | predicted top 30) - mean(realized_target_percentile | predicted bottom 30)`

This measures separation quality and is less dependent on absolute market direction.

## Consensus-shortlist evaluation

The frozen product consensus is:

`alpha_consensus = 0.5 * predicted_h5_percentile + 0.5 * predicted_h10_percentile`

For evaluation only, define a matching realized consensus target:

`realized_consensus = 0.5 * target_rank_h5 + 0.5 * target_rank_h10`

on rows where both targets are defensibly observable.

Primary consensus metrics:

- daily Spearman IC between `alpha_consensus` and `realized_consensus`;
- top-30 mean realized consensus percentile/score;
- top-30 minus bottom-30 realized consensus spread.

The component H5/H10 metrics remain mandatory and may not be hidden by a strong consensus result.

## Raw-return economic diagnostics

Raw `R5` and `R10` are preserved even though the alpha target is rank-based.

For each horizon, report as secondary diagnostics:

- equal-weight predicted-top-30 raw return;
- eligible-universe equal-weight raw return;
- top-30 minus universe raw-return spread;
- median stock raw return within predicted top 30;
- proportion of top-30 names with positive raw return.

These diagnostics provide economic interpretability but do not turn Alpha into an Expected Payoff or Path Risk model.

## Shortlist size

The recommended frozen evaluator shortlist is **Top 30**.

Reasoning is product-level, not backtest-derived:

- the eligible IDX universe is expected to remain several hundred names;
- 30 is small enough to represent meaningful narrowing before downstream Path Risk/Decision layers;
- it is large enough to avoid an evaluator dominated by a few single-name outliers;
- it matches the user's intended practical shortlist scale of roughly 20–30 names.

Top 20 may be reported only as a secondary sensitivity diagnostic if preregistered before outcomes. It must not replace Top 30 because historical results look better.

## Breadth and concentration diagnostics

Every fold must report whether apparent performance is concentrated in a narrow subset of:

- dates;
- tickers;
- liquidity strata;
- sectors if PIT sector state is available and admitted;
- market regimes using decision-time observable context only.

At minimum report ticker contribution concentration and date contribution concentration.

A high aggregate score driven by a tiny set of repeated names is not automatically robust evidence.

## Challenger-versus-control rule

V4-3 will freeze the initial control/model family. Once a control exists, all challengers must be evaluated as paired comparisons on identical dates and rows.

For each horizon and consensus, report paired date-level challenger-minus-control deltas for:

- daily Spearman IC;
- top-30 realized target score;
- top-30 minus bottom-30 spread.

The control must remain eligible to win. A challenger is not promoted merely because one pooled metric is larger.

Recommended eventual promotion shape before any outcomes are seen:

1. no material degradation on either H5 or H10 primary rank quality;
2. positive typical paired improvement on at least one horizon;
3. positive consensus shortlist improvement;
4. lower-tail/fold robustness must not materially worsen;
5. no severe breadth/concentration regression;
6. raw-return diagnostics must not reveal an obvious economic contradiction.

Exact numerical promotion thresholds should be frozen in V4-3 together with the initial control and candidate family, rather than retrofitted after results.

## What is not a primary metric

The following may be diagnostic but are not primary V4-2 evidence:

- pooled row-level ROC-AUC;
- pooled PR-AUC;
- classification accuracy;
- TP-first / SL-first success rate;
- simulated portfolio PnL;
- Sharpe ratio;
- Kelly growth;
- drawdown-adjusted alpha score.

Those either belong to the old binary ontology or to downstream Decision/Portfolio/Execution research.

## Fresh confirmation boundary

Historical evidence through 2026-07-31 is development evidence even though the target contract is new.

A model/candidate selected using that history requires genuinely fresh prospective confirmation after all target, evaluator, feature, model-family, and promotion rules are frozen.

The existing O2 100-session forward counter cannot automatically validate V4 because it belongs to a different target/model lineage.

## Recommended V4-2 lock direction

- `DATE_CENTRIC_EVALUATION`
- separate H5 and H10 rank-quality evidence;
- mandatory 50/50 consensus-shortlist evidence;
- Top 30 as the fixed practical shortlist evaluator;
- six expanding 100-session validation folds with H10-governed purge;
- paired exact-common-support comparisons;
- raw-return diagnostics secondary;
- no PnL/sizing/execution optimization at Alpha stage;
- exact numerical promotion thresholds deferred until V4-3 freezes the control/candidate family, but metric definitions cannot change after V4 outcomes are viewed.

Provisional verdict:

`V4_2_DATE_CENTRIC_H5_H10_CONSENSUS_EVALUATOR_RECOMMENDED_NOT_YET_LOCKED`

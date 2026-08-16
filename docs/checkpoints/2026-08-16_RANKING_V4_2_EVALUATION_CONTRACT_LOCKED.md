# Ranking V4-2 — Evaluation and Promotion Contract Locked

Date: 2026-08-16 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-2-evaluation-contract-v1`
Parent V4-1 lock: `199d770520edcd4a7b4537c75d5edaba2b0aa349`
Status: `V4_2_DATE_CENTRIC_H5_H10_CONSENSUS_EVALUATOR_LOCKED_NO_MODEL_OR_OUTCOME_RUN`

## Purpose

V4-2 freezes how Alpha V4 will be judged before any V4 historical target is materialized, any model is fit, or any V4 outcome is inspected.

V4-0 and V4-1 remain controlling:

- Alpha V4 is an opportunity ranker only.
- Alpha-H5 and Alpha-H10 are separately fitted artifacts using the same initial upstream pipeline and different frozen H5/H10 rank targets.
- the product consensus is the outcome-blind 50/50 average of within-date H5/H10 predicted percentile scores;
- H5/H10 are forecast horizons, not mandatory exits;
- Path Risk, payoff/probability, trade selection, sizing, execution, and paper/live accounting remain separate layers.

## Primary unit of evidence

The primary unit of evidence is the **decision date**, not the pooled security row.

Each EOD session creates one cross-sectional ranking decision over the decision-time eligible universe. Therefore each eligible decision date has equal scientific weight in the primary summaries, regardless of whether 400 or 800 securities happen to have observable targets.

Pooled row-level metrics may be reported only as diagnostics.

## Locked historical-development validation shape

The initial V4 historical-development protocol is:

- chronological expanding-window validation;
- six validation folds;
- each validation fold spans 100 consecutive eligible signal sessions;
- training uses only dates strictly before the validation block;
- the longest frozen label horizon, H10, governs purge;
- at least 10 signal sessions immediately before each validation block are excluded from training so no training label reaches into the validation information window;
- no random split;
- no future-data interpolation;
- no post-result fold-boundary changes;
- exact official-session identities must be materialized and hash-pinned before any outcome calculation.

If a pre-outcome support census shows that the six-by-100 structure is not technically feasible under the locked data-admission rules, the run is **BLOCKED**. The fold structure may not be changed after performance is viewed to rescue the experiment.

## Locked target-observability discipline

For every signal date `t`, the scoring population is determined from EOD-`t` information only.

Future target states are tracked separately and may include:

- `TARGET_H5_AVAILABLE`
- `TARGET_H10_AVAILABLE`
- `TARGET_BOTH_AVAILABLE`
- `MARKET_ENTRY_UNAVAILABLE`
- `TARGET_DATA_UNOBSERVABLE`
- `PRICE_CONTINUITY_UNRESOLVED`
- `TRADING_MECHANISM_REFERENCE_UNRESOLVED`
- another enumerated fail-closed state required by implementation.

A negative, zero, sideways, or otherwise unattractive realized return is never a missing target.

No future-unobservable row may be silently removed from the original decision ledger.

### Primary date-level observability gate

For a horizon-specific daily primary metric to be admitted, at least **90% of the EOD-scored decision-time population** on that date must have a defensibly observable target for that horizon.

For the H5/H10 consensus daily primary metric, at least **90% of the EOD-scored population** must have both targets defensibly observable.

Dates below the relevant gate are recorded as `DATE_METRIC_INSUFFICIENT_TARGET_COVERAGE` and do not enter the primary daily-metric summary. Their counts and causes must remain visible.

This gate is a data-quality rule, not a performance filter.

### Top-30 observability gate

The predicted Top 30 is selected from the full EOD-scored decision-time population before any future target state is known.

A Top-30 date-level metric is primary-admissible only when at least **27 of the original 30 predicted names** have a defensibly observable target for that metric. The realized denominator and all missing-state reasons must be reported.

The evaluator may not refill missing Top-30 names with ranks 31, 32, etc. after future observability is known.

## Target continuity and market-mechanism gate

The locked V4 target begins at official `Open_(t+1)`. Before target materialization, an outcome-blind support/continuity census must verify that the historical reference is defensible on the intended population.

Hard rules:

- no synthetic Open reconstruction for V4 target labels;
- no use of `Close_t` as a substitute entry benchmark;
- splits, stock dividends, rights events, reverse splits, or other mechanical price discontinuities must be continuity-resolved under an admitted point-in-time corporate-action policy, otherwise the row is `PRICE_CONTINUITY_UNRESOLVED`;
- if a security's trading mechanism makes the meaning of the intended `Open_(t+1)` research reference unresolved, the row is `TRADING_MECHANISM_REFERENCE_UNRESOLVED` rather than guessed;
- cash-dividend total-return treatment is not added to Alpha V4 under the locked price-return target. V4 therefore predicts relative **price** performance, not total shareholder return.

The support/continuity census may block target materialization but may not change V4-1's target definition after outcomes are viewed.

## Locked horizon metrics

H5 and H10 are evaluated independently.

For each admitted decision date and horizon:

### 1. Daily cross-sectional Spearman IC

Spearman rank correlation between model score and realized within-date target percentile.

Per fold report:

- mean daily IC;
- median daily IC;
- fraction of positive-IC dates;
- lower quartile;
- lower-tail / dispersion diagnostics.

Across folds emphasize median and lower-quartile robustness, not only the grand pooled average.

### 2. Predicted Top-30 mean realized target percentile

Select the 30 highest-scored securities from the full EOD scoring population and measure the mean realized target percentile on the original predicted names that pass the locked observability gate.

An uninformed ranking has expected realized percentile near the cross-sectional center; higher is better.

### 3. Predicted Top-30 minus Bottom-30 realized target spread

For each admitted date:

`mean(realized_target_percentile | predicted top 30) - mean(realized_target_percentile | predicted bottom 30)`

The same no-refill and observability accounting rules apply to both tails.

## Locked consensus evaluation

The frozen product consensus remains:

`alpha_consensus = 0.5 * alpha_h5_percentile + 0.5 * alpha_h10_percentile`

where component scores are preserved separately and normalized within each decision date before the 50/50 combination.

On rows with both defensible targets:

`realized_consensus = 0.5 * target_rank_h5 + 0.5 * target_rank_h10`

Primary consensus metrics are:

- daily Spearman IC;
- predicted Top-30 mean realized consensus score;
- predicted Top-30 minus Bottom-30 realized consensus spread.

A strong consensus result may not hide a material H5 or H10 failure.

## Locked shortlist size

**Top 30** is the only primary shortlist size for the initial V4 evaluator.

It is frozen for product reasons: it materially narrows a several-hundred-name universe while remaining broad enough not to let a handful of single-name outliers dominate the evaluator.

Top 20, Top 50, top-decile, or other shortlist sizes are not permitted as post-result rescue metrics for the initial V4 generation.

## Raw-return economic diagnostics

For H5 and H10 separately, preserve raw `R5` and `R10` and report:

- equal-weight raw return of the predicted Top 30;
- equal-weight raw return of the eligible observable universe;
- Top-30 minus universe raw-return spread;
- median raw return within predicted Top 30;
- fraction of predicted Top-30 names with positive raw return.

These are mandatory diagnostics, not Alpha training targets and not portfolio-PnL claims.

## Dependence-aware uncertainty

Daily H5/H10 labels overlap because consecutive signal dates share future observation windows. Treating daily metrics as IID would overstate effective sample size.

Therefore uncertainty summaries for primary daily metrics must use a **moving date-block bootstrap with 10-session blocks**, governed by the longest H10 outcome window.

Initial implementation parameters are frozen as:

- block length: 10 consecutive eligible signal sessions;
- bootstrap replications: 2,000;
- deterministic seed: 42;
- confidence interval: two-sided 95% percentile interval.

Fold-level point estimates remain mandatory; bootstrap intervals supplement rather than replace fold robustness.

## Breadth, concentration, and missingness diagnostics

Every fold must report:

- date contribution concentration;
- ticker contribution concentration;
- target-unobservability rate by date;
- target-unobservability rate by predicted-score decile;
- target-unobservability by decision-time liquidity stratum;
- trading-mechanism / board state when point-in-time data are admitted;
- sector breakdown only when PIT sector state is separately admitted;
- decision-time market-regime breakdown only using causal context.

Performance driven by a tiny group of dates/tickers or by selectively observable targets is not robust evidence.

## Challenger-versus-control discipline

V4-3 will freeze the initial control and candidate/model family before outcomes.

All challenger comparisons must use paired exact common support for the relevant metric and report date-level challenger-minus-control deltas for:

- daily Spearman IC;
- Top-30 realized target score;
- Top-30 minus Bottom-30 spread;
- consensus counterparts.

The control must be allowed to win.

Exact numerical promotion thresholds are deferred to V4-3 because they must be tied to the exact frozen control/candidate family, but V4-2 metric definitions, Top-30 size, observability gates, dependence treatment, and date-centric evidence may not change after V4 outcome access.

## Not primary Alpha evidence

The following are not primary V4-2 metrics:

- pooled ROC-AUC;
- pooled PR-AUC;
- classification accuracy;
- TP-first / SL-first hit rate;
- simulated portfolio PnL;
- Sharpe ratio;
- Kelly growth;
- drawdown-adjusted alpha utility;
- ex-post best-exit performance.

They either belong to the old target ontology or to downstream Decision/Portfolio/Execution research.

## Fresh confirmation boundary

All history through 2026-07-31 is development knowledge.

Even if the V4 target is new, selecting a model/features/promotion rule on that history does not create independent confirmation. Final validation requires genuinely fresh prospective data collected only after target, evaluator, features, learner, and promotion rules are frozen.

The protected O2 100-session lineage is not automatically reusable as V4 validation because its research question and model lineage differ.

## Final locked statement

> V4 Alpha will be evaluated as one cross-sectional decision per EOD date. Alpha-H5, Alpha-H10, and their frozen 50/50 consensus are judged separately using daily rank IC and a fixed predicted Top-30 shortlist, with exact no-refill target-observability accounting, a 90% date-level target-coverage gate, 27/30 Top-30 target observability, H10-governed purge, six expanding 100-session validation blocks, and 10-session moving-block-bootstrap uncertainty. Raw returns remain mandatory economic diagnostics. Corporate-action continuity and `Open_(t+1)` trading-reference semantics must pass a pre-outcome support census before any V4 target materialization. No pooled metric, PnL simulation, alternative shortlist size, or post-result evaluator change may rescue the initial V4 generation.

Verdict:

`V4_2_DATE_CENTRIC_H5_H10_CONSENSUS_EVALUATOR_LOCKED_NO_MODEL_OR_OUTCOME_RUN`

Next allowed step before model fitting: **V4 target-support / Open / continuity census and exact fold-boundary materialization, outcome-blind**.

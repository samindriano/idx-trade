# Closed Alpha Family Re-evaluation

Date: 2026-08-26 Asia/Jakarta
Branch: `research/idx-alpha-frontier-v1`
Status: `METHODOLOGY_REVIEW_COMPLETE`

## Purpose

Re-read the closed Financial PIT and Foreign Flow alpha experiments to distinguish:

1. rejection of one exact representation/target/model-role hypothesis; from
2. evidence that an entire information family has no exploitable edge.

The audit does not reopen consumed historical folds, run new models, inspect protected prospective outcomes, or authorize post-hoc rescue tuning.

## Main conclusion

The prior research process was strong on causality, reproducibility, preregistration, common support, and anti-overfitting controls, but comparatively weak on hypothesis discovery and mechanism diagnosis before model fitting.

The previous `NO_SURVIVOR` verdicts must therefore be interpreted narrowly. They reject the exact preregistered challenger experiment. They do **not** establish that the underlying data family has no edge in every horizon, conditional state, portfolio role, or target formulation.

## Foreign Flow

### What was actually tested

Foreign Flow V2 Core tested one exact hypothesis:

- Clean V2 25-feature HGB control;
- plus eight Foreign Flow V2 features simultaneously;
- fresh HGB fit with the same model hyperparameters;
- binary H10 `TP_FIRST` versus `SL_FIRST` target;
- paired expanding folds;
- primary gate based on PR-AUC delta, with ROC/Q5-Q1 guardrails.

Exact eight-feature block:

1. `foreign_participation_1`
2. `foreign_flow_shock_percentile_120`
3. `xs_rank_foreign_flow_shock_mean_5`
4. `xs_rank_foreign_flow_shock_mean_20`
5. `foreign_weighted_persistence_5`
6. `foreign_flow_acceleration_5_20`
7. `foreign_flow_price_divergence_5`
8. `foreign_flow_price_divergence_20`

Result: median paired PR-AUC delta about `-0.004294`, q25 negative, only `1/6` positive PR-AUC folds. The exact additive H10 challenger therefore correctly failed.

### Why that does not close the information family

Several alternative mechanisms were not tested by that experiment:

- foreign flow as an event/extreme-tail signal rather than a universal continuous feature;
- foreign flow as a conditional setup state interacting with price state, liquidity, or supply tightness;
- reversal versus continuation asymmetry;
- different return horizons or decay curves;
- cross-sectional forward-return IC rather than binary path classification;
- portfolio-entry filtering or confirmation rather than direct alpha ranking;
- supply-adjusted demand pressure using defensible PIT tradable-supply information;
- market-wide foreign-flow regime and stock-level sensitivity interactions.

The experiment also added all eight features to a monolithic classifier at once. Failure of the combined model cannot identify whether one mechanism is useful but diluted by unrelated/noisy dimensions.

The old representation audit itself discovered very large unresolved shock outliers/clusters and explicitly retained them without clipping or semantic reinterpretation. Those observations were treated as data-quality diagnostics rather than investigated as economic event states. That was scientifically conservative but limited hypothesis discovery.

### Updated interpretation

Binding historical result remains:

`FOREIGN_FLOW_V2_CORE_NO_SURVIVOR`

Updated family-level interpretation:

`FOREIGN_FLOW_UNIVERSAL_ADDITIVE_H10_ALPHA_NOT_SUPPORTED`

but **not**:

`FOREIGN_FLOW_HAS_NO_EDGE`.

The strongest legitimate future path is mechanism-first / conditional-state research on fresh or separately protected data, not post-hoc V2 feature rescue on the consumed six folds.

## Financial PIT

### What was actually tested

Financial Alpha V1 used:

- 13 accounting features;
- separated across Q1/H1/9M/FY, producing 52 slots;
- Clean V2 + Financial versus a Clean V2 control;
- H10 binary path target;
- only Financial-era eligible folds V2F4/V2F5/V2F6;
- common support of 70,520 rows / 321 tickers.

Result: median PR-AUC delta was slightly positive, but q25 was negative, ROC and Q5-Q1 guardrails worsened, so the exact challenger failed.

### Why that does not close the information family

The experiment is especially vulnerable to target/representation mismatch because financial statements are slow-moving information while the target is short-horizon H10 path classification.

Important economic representations not tested include:

- filing-event surprise versus prior filing/consensus-like baseline;
- change/acceleration in margins, profitability, leverage, or cash conversion;
- sector-relative and size-relative fundamental ranks;
- valuation interaction with quality/growth;
- earnings-quality and accrual-style constructions;
- filing revision/restatement events;
- post-filing drift / delayed reaction;
- longer-horizon cross-sectional returns;
- fundamentals as risk/eligibility/context rather than direct 10-day alpha.

The support itself was narrow: only 321 tickers and three eligible folds in the completed V1 test. A later outcome-blind structural audit found a compact `CORE3` representation was structurally admissible, while YoY features had inadequate early-fold training support. Financial Alpha V2 was never run.

### Updated interpretation

Binding result remains:

`FINANCIAL_PIT_ALPHA_V1_NO_SURVIVOR`

Updated family-level interpretation:

`GENERIC_ACCOUNTING_LEVELS_AS_ADDITIVE_H10_FEATURES_NOT_SUPPORTED`

but **not**:

`FINANCIAL_DATA_HAS_NO_EDGE`.

A future financial hypothesis should be event/change/relative-value oriented and should use a horizon aligned with the economic mechanism. It should not simply retry generic ratio levels on the consumed V1 design.

## Other historical data lanes

- Margin: old work primarily rejected the **source interpretation** as actual margin usage/flow. This is not an alpha false-negative problem; the intended signal itself was unsupported by source semantics.
- Ownership/free-float/HSC: source work became deep, but there was no final comprehensive alpha experiment. Do not classify the family as alpha-rejected.
- Suspension/resumption: data-state engineering exists; no broad standalone alpha conclusion was established.
- Price/trend state: retained as a descriptive/sidecar architecture; not equivalent to a universal alpha rejection.

## Process change for Alpha Frontier V1

For new data families, do not jump directly from dataset acquisition to `incumbent + feature block` model fitting.

Required sequence:

1. certify source semantics and PIT timing;
2. perform outcome-blind EDA and distribution/state diagnostics;
3. articulate economic mechanisms and competing predictions;
4. freeze a small set of hypotheses;
5. test univariate IC, quantile/event studies, decay, monotonicity, and conditional behavior;
6. diagnose where the effect exists and where it does not;
7. only then test incremental value versus the frozen incumbent on common support;
8. distinguish alpha, context/filter, regime, risk, and execution roles;
9. reserve genuinely unseen data for confirmation.

## Research-budget rule

Do not use this audit to mine the already-consumed Foreign Flow V1/V2 or Financial V1 folds for a rescue configuration. Historical results can motivate architecture-level questions, but any new hypothesis derived after seeing those outcomes must be validated on fresh/protected evidence or a separately justified untouched period.

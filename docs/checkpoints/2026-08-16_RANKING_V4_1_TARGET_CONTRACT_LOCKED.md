# Ranking V4-1 — Target Contract Locked

Date: 2026-08-16 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-1-target-contract-v1`
Parent V4-0 contract: `research/idx-ranking-v4-0-decision-contract-v1`
Status: `V4_1_TWO_HEAD_H5_H10_RANK_TARGETS_LOCKED_NO_MODEL_OR_OUTCOME_RUN`

## Locked purpose

Alpha V4 remains an opportunity-ranking layer only. V4-1 freezes the supervised target family before any V4 historical label materialization, model fit, feature search, or performance comparison.

## Locked timing

For a signal date/session `t`:

- information cutoff is validated EOD `t`;
- the future benchmark begins at official `Open_(t+1)`;
- `Close_t` is prohibited as a post-signal entry/fill reference;
- `Open_(t+1)` is a research benchmark, not a claim that a real limit order fills there.

## Locked target family

V4 uses two separate forward-return horizons:

`R5 = Close_(t+5) / Open_(t+1) - 1`

`R10 = Close_(t+10) / Open_(t+1) - 1`

Each raw return is transformed within the same decision date into a cross-sectional relative target, with the initial frozen target representation being within-date percentile rank.

Thus each decision row has two supervised targets when both are defensibly observable:

- `target_rank_h5`
- `target_rank_h10`

Raw `R5` and `R10` must also be preserved as diagnostics/provenance fields, but Alpha V4 does not train to predict exact return magnitude under this contract.

## Locked model separation principle

V4 will begin with two separately fitted alpha models:

- `Alpha-H5`
- `Alpha-H10`

They are separate fitted artifacts because their supervised targets differ.

For the first clean comparison, they should use the same upstream feature matrix, universe contract, model-family choice, preprocessing logic, and initial hyperparameter/configuration policy unless a later preregistered experiment explicitly changes one dimension.

The implementation may use one reusable training function parameterized by horizon, but the resulting fitted models remain distinct.

A shared multi-task/multi-output learner is not part of the initial V4 contract. It may only appear later as a separately preregistered challenger after independent H5/H10 baselines exist.

## Locked interpretation

H5 and H10 are forecast horizons, not mandatory exit horizons.

- H5 asks which stocks are likely to outperform peers over roughly one trading week.
- H10 asks which stocks are likely to outperform peers over roughly two trading weeks.
- A live position may be exited earlier or later by a separately validated downstream Decision/Execution policy using new information available after entry.
- A high H5 score and low H10 score can represent a fast but less persistent opportunity; a high score at both horizons can represent stronger persistence. These interpretations are descriptive only and do not authorize an exit rule.

## Locked consensus shortlist score

For product-level alpha shortlisting, preserve both horizon scores and define the initial transparent consensus as an equal-weight average of the two predicted within-date percentile scores:

`alpha_consensus = 0.5 * alpha_h5_percentile + 0.5 * alpha_h10_percentile`

The 50/50 rule is frozen as a product prior representing equal importance of approximately one-week and two-week swing opportunity. It is not selected by backtest optimization.

The component H5 and H10 scores must always remain visible/auditable; the consensus may not replace them in stored artifacts.

The exact shortlist size (for example top 20, top 30, or a percentage of the eligible universe) is not a target property and remains a V4-2 evaluation / later Decision-layer choice.

## Explicitly rejected as primary Alpha V4 targets

- resolved-only TP-first versus SL-first labels;
- future maximum/MFE within the window;
- ex-post best exit timing;
- return-minus-drawdown or other alpha/risk blended utilities;
- a single H10 terminal return as the only V4 alpha truth;
- H3/H6/H7/H15/H20 horizon expansion in the initial V4 target contract;
- choosing horizon weights after observing historical performance.

## Population and missingness

The decision-time scoring population is determined using only information available by EOD `t`.

Future events may not retroactively erase a signal row. Market entry unavailable, target-data unobservable, corporate-action continuity unresolved, or other future states must be represented explicitly and fail closed where the return target cannot be defensibly computed.

Rows must never be dropped merely because future return is small, negative, sideways, or otherwise unattractive.

## Relationship to downstream layers

The target intentionally does not encode:

- adverse path / drawdown (Path Risk);
- exact payoff magnitude (Expected Payoff);
- probability calibration;
- reliability filtering;
- trade/no-trade policy;
- position sizing;
- limit price / fill probability / slippage / fees;
- exit timing.

Those remain separate research contracts under V4-0.

## Research governance lock

After this checkpoint:

- H5/H10 target definitions and equal consensus weights may not be changed in response to V4 historical results;
- no additional horizon may be introduced as a rescue after outcome access;
- no future-max or risk-adjusted target may be substituted after seeing results;
- any alternative target family requires a separately preregistered generation/challenger, not a V4 rescue;
- historical data through 2026-07-31 remains development knowledge and cannot by itself provide final independent confirmation.

## Final locked statement

> Alpha V4 begins with two separately fitted cross-sectional opportunity models sharing the same initial pipeline but learning different fixed forecast horizons: H5 and H10. Both targets are within-date percentile ranks of raw return measured from `Open_(t+1)` to the corresponding fixed close. H5/H10 are forecast horizons, not forced exits. The product may use an outcome-blind 50/50 consensus of the two predicted percentile scores for shortlisting while retaining both component scores. Risk, payoff magnitude, trade selection, sizing, execution, and exit timing remain separate modules.

Verdict:

`V4_1_TWO_HEAD_H5_H10_RANK_TARGETS_LOCKED_NO_MODEL_OR_OUTCOME_RUN`

Next authorized stage: **V4-2 Evaluation and Promotion Contract**, outcome-blind.
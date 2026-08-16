# Ranking V4-1 — Target Research Recommendation

Date: 2026-08-16 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-1-target-contract-v1`
Status: `V4_1_TARGET_RESEARCH_RECOMMENDATION_RECORDED_NOT_LOCKED_NO_OUTCOME_RUN`

## Scope

Outcome-blind target-design research only. No historical V4 target was materialized, no model was fit, no protected/fresh-forward outcome was accessed, no feature search was performed, and no V4-1 target was frozen by this note.

V4-0 remains controlling: Alpha V4 is an opportunity ranker after EOD `t`; Path Risk, payoff/probability, decision, sizing, execution, and paper/live accounting remain separate layers.

## Literature-backed lessons

1. Cross-sectional equity ML commonly predicts fixed forward holding-period returns and then ranks securities. Learning-to-rank research explicitly distinguishes score calculation, ranking, selection and portfolio construction; it also notes that regress-then-rank models conventionally use future holding-period returns as supervised targets.
2. Forecast horizon is not a cosmetic choice. Evidence across multiple studies shows return predictability and predictor importance can differ substantially across horizons; one horizon should not be assumed to represent another.
3. Target representation itself is first-order. Recent international evidence reports that cross-sectional standardization or rank transformation of future returns can materially improve prediction versus raw return targets. Rank targets are especially aligned with ranking problems but discard return magnitude.
4. Longer-horizon return targets can reduce turnover and select slower signals, but they are a different economic problem rather than a free robustness improvement.

## Candidate target families adjudicated conceptually

### A. Single terminal H10 return

`R10 = Close_(t+10) / Open_(t+1) - 1`

Pros:
- simplest;
- conventional fixed-horizon holding-period target;
- easy to reproduce and purge;
- no oracle exit timing.

Cons:
- endpoint-sensitive;
- a setup that produces a large one-week swing and then mean-reverts by H10 can be labelled poorly despite a genuine earlier opportunity;
- makes H10 appear more economically authoritative than warranted.

Verdict: `VALID_SIMPLE_BASELINE_BUT_TOO_ENDPOINT_SENSITIVE_AS_ONLY_V4_ALPHA_TRUTH`.

### B. Future maximum/MFE within H10

Pros:
- captures early opportunities.

Cons:
- uses an ex-post best future point;
- implicitly gives the alpha layer an oracle exit;
- conflates opportunity prediction with exit/decision mechanics;
- vulnerable to one-bar spikes and intraday observability assumptions.

Verdict: `REJECT_AS_PRIMARY_ALPHA_TARGET`.

### C. Barrier/TP-first-vs-SL-first

Pros:
- path-aware;
- familiar from V1-O2.

Cons:
- reintroduces the old barrier ontology;
- can condition sample membership on future resolution if unresolved/no-hit cases are dropped;
- mixes alpha with risk/exit geometry.

Verdict: `REJECT_FOR_V4_ALPHA_CORE`.

### D. Risk-adjusted return target

Examples: return minus drawdown penalty, Sharpe-like path target, ATR-risk penalty.

Pros:
- economically intuitive as one scalar.

Cons:
- violates the V4-0 modular boundary by mixing Alpha and Path Risk;
- makes later attribution/debugging difficult.

Verdict: `REJECT_FOR_ALPHA; KEEP_RISK_SEPARATE`.

### E. Multi-horizon H5/H10 alpha

Define two future holding-period returns from the same post-signal benchmark:

- `R5 = Close_(t+5) / Open_(t+1) - 1`
- `R10 = Close_(t+10) / Open_(t+1) - 1`

Then transform each return within the same decision date into a cross-sectional relative target. Two implementation variants remain scientifically reasonable:

1. **two-horizon heads/models**: learn H5 and H10 targets separately, preserve both predicted horizon scores, and combine them only through a frozen transparent consensus rule;
2. **single composite target**: combine frozen transformed H5/H10 targets with fixed weights before training.

The research recommendation favors the first variant because evidence indicates different horizons may contain different dynamics. Separate heads preserve interpretability and avoid forcing one model to average distinct horizon mechanisms internally.

For an Alpha-only system, within-date percentile-rank targets are highly aligned with the product task and robust to market-wide level shifts. Raw forward returns should still be preserved as diagnostics and for future Expected Payoff research. A standardized-return challenger may later be justified because rank transforms discard magnitude, but no target-transform tournament should be run post hoc on consumed history.

## Recommended V4-1 direction for user review

Primary conceptual target family:

`MULTI_HORIZON_RELATIVE_RETURN_H5_H10`

with:

- information cutoff after EOD `t`;
- future benchmark begins at `Open_(t+1)`;
- two predefined checkpoints: `Close_(t+5)` and `Close_(t+10)`;
- one cross-sectional target per horizon, preferably within-date percentile rank for the initial clean alpha formulation;
- no H3/H6/H20 expansion in the initial contract;
- no future-max/MFE label;
- no risk/drawdown penalty in the alpha label;
- no actual exit assumption implied by H5/H10 measurement checkpoints.

A practical model can later emit:

- `alpha_h5_score`;
- `alpha_h10_score`;
- a frozen transparent consensus score, e.g. equal-weight average of the two within-date predicted percentiles, if the user explicitly approves this as the product definition before outcomes are run.

Equal weighting is recommended as a product prior only if the intended swing window is genuinely one-to-two weeks. It must not be selected because it backtests best.

## Interpretation of the early-peak/reversal example

Suppose a stock starts from the V4 benchmark, is strongly positive around H5, but reverses below entry by H10.

Under a single H10 target, it is labelled only as a loser.

Under the proposed two-horizon formulation:

- H5 target can be strong;
- H10 target can be weak;
- the system can explicitly see `fast opportunity / poor persistence` instead of collapsing the path into one endpoint.

This does not assume the trader knew to sell at the H5 peak. H5 is a predetermined evaluation checkpoint, not an ex-post best exit. Future Decision/Execution layers may separately learn or enforce exit rules using only information available at their own decision time.

## Why not add many horizons immediately

Adding H3/H5/H7/H10/H15/H20 would create substantial design degrees of freedom and highly overlapping labels. The project should first test a minimal horizon structure with clear product meaning. H5 and H10 naturally bracket approximately one and two trading weeks and are simple enough for explicit purge/maturity semantics.

## Next unresolved choice before lock

The user should approve one of these two variants before V4-1 is frozen:

### Recommended

`TWO_HEAD_H5_H10_RANK_TARGETS`

- separate horizon targets;
- retain separate scores;
- optionally define an equal-weight consensus ranking as the Alpha shortlist score.

### Simpler control

`SINGLE_H10_RANK_TARGET`

- much simpler;
- valid benchmark;
- accepted endpoint-sensitivity tradeoff.

No historical performance comparison between these variants is authorized before the product choice is frozen.

## Current recommendation

`RECOMMEND_TWO_HEAD_H5_H10_RELATIVE_RETURN_TARGETS_OVER_SINGLE_H10_OR_FUTURE_MAX`

This is a design recommendation, not a locked V4-1 contract.

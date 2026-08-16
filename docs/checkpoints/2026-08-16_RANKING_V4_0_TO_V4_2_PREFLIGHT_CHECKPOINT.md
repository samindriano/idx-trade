# Ranking V4 — V4-0 to V4-2 Preflight Scientific Checkpoint

Date: 2026-08-16 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-2-evaluation-contract-v1`
Status: `V4_0_TO_V4_2_PREFLIGHT_GO_CONCEPTUAL_CONTRACTS_FROZEN_TARGET_MATERIALIZATION_REQUIRES_SUPPORT_CENSUS`

## Why this checkpoint exists

This is the last conceptual review before V4 target materialization/model work. The purpose is to challenge V4-0, V4-1, and V4-2 one by one against the legacy forensic findings, external finance/ML research, current IDX trading mechanics, and implementation failure modes.

No V4 historical targets were materialized, no V4 model was fit, and no V4 performance outcome was inspected during this checkpoint.

The standard here is not "the design is guaranteed to make money." The standard is:

1. the research question matches the intended product;
2. the target is economically and temporally coherent;
3. the evaluator can falsify the model without hidden rescue degrees of freedom;
4. known data/mechanics limitations are explicit hard gates;
5. future changes require a new preregistered challenger/generation rather than retroactive editing of V4.

## V4-0 audit — product and module boundary

### Locked design

After validated EOD session `t`, Alpha V4 ranks the decision-time eligible IDX universe for relative future swing-long opportunity. Alpha is not BUY/SELL, risk acceptance, sizing, order placement, fill simulation, or exit timing.

Separate downstream modules remain:

- Path Risk;
- payoff/probability if separately validated;
- reliability/uncertainty;
- Decision Engine;
- portfolio/sizing;
- execution;
- paper/shadow and real ledgers.

### External research check

Cross-sectional systematic-strategy research explicitly treats ranking as a stage prior to portfolio construction. Learning-to-rank research in finance focuses on improving the ordering of assets before portfolio formation rather than requiring the prediction model to encode portfolio weights or execution itself. This supports the V4 modular boundary.

Relevant primary sources reviewed:

- Poh, Lim, Zohren, Roberts, *Building Cross-Sectional Systematic Strategies By Learning to Rank* (arXiv:2012.07149).
- Zhang, Wu, Chen, *Constructing long-short stock portfolio with a new listwise learn-to-rank algorithm* (arXiv:2104.12484).
- Gu, Kelly, Xiu, *Empirical Asset Pricing via Machine Learning*, Review of Financial Studies 33(5), 2020, DOI 10.1093/rfs/hhaa009.

### Current IDX mechanics check

The current IDX trading-mechanics page, under BEI Rule II-A / Kep-00003/BEI/04-2025, states that regular-market pre-opening input occurs before the 09:00 session and that the Opening Price is formed from pre-opening order accumulation/matching. Unmatched pre-opening orders can flow into Session I subject to the applicable rules.

This supports the economic ordering:

`EOD t information -> model/ranking after close -> future market action begins t+1`.

It does **not** prove that a user's broker accepts overnight orders or that a user's limit order fills exactly at the official Open. Broker submission timing, limit matching, partial fills, and slippage remain Execution-layer questions.

Official source reviewed: Indonesia Stock Exchange, *Jam dan Mekanisme Perdagangan*, current page referencing Kep-00003/BEI/04-2025.

### V4-0 red-team findings

No foundation-level flaw found.

The old `Close_t` pseudo-entry problem is removed. Operational miss, non-fill, true market unavailability, and research-data missingness are separated. Paper-vs-real ledgers remain the correct way to attribute human execution drift without corrupting model evaluation.

### V4-0 final checkpoint verdict

`GO — KEEP LOCKED`.

No return to an all-in-one opaque alpha/risk/sizing/execution model is authorized for the initial V4 generation. A future shared/multi-task architecture can only be a separately preregistered challenger after modular baselines exist.

## V4-1 audit — H5/H10 cross-sectional rank targets

### Locked design

For signal session `t`:

- benchmark starts at official `Open_(t+1)`;
- `R5 = Close_(t+5) / Open_(t+1) - 1`;
- `R10 = Close_(t+10) / Open_(t+1) - 1`;
- each return is converted to a within-date cross-sectional percentile-rank target;
- Alpha-H5 and Alpha-H10 are fitted separately;
- initial feature matrix/model-family/configuration policy is shared for a fair horizon comparison;
- product shortlist consensus is the frozen 50/50 average of within-date predicted H5/H10 percentile scores;
- H5/H10 are rolling forecast horizons, not mandatory trade exits.

### External research check — fixed forward returns

Fixed future holding-period return prediction followed by cross-sectional sorting is standard in empirical asset-pricing ML. Gu, Kelly, and Xiu predict future stock returns and form prediction-sorted portfolios; the broader cross-sectional forecast literature similarly distinguishes forecast quality from portfolio construction.

A Japanese cross-sectional investment-management study explicitly uses information available at market close and invests at the next market opening, showing that the close-to-next-open decision ordering is a recognized implementable research pattern rather than a V4-specific invention.

Relevant sources reviewed:

- Gu, Kelly, Xiu (2020), Review of Financial Studies.
- Abe & Nakagawa, *Cross-sectional Stock Price Prediction using Deep Learning for Actual Investment Management* (arXiv:2002.06975).
- Han, He, Rapach, Zhou, *Cross-sectional expected returns: new Fama-MacBeth regressions in the era of machine learning*, Review of Finance 28(6), 2024.

### External research check — rank target

Recent international evidence finds that the target representation itself is a first-order design choice: standardized/rank-transformed future returns can materially improve cross-sectional prediction, while rank transforms intentionally discard magnitude information.

That tradeoff fits V4's modular design:

- Alpha predicts relative ordering;
- Expected Payoff, if later revived successfully, owns magnitude;
- Path Risk owns adverse-path characterization.

Primary source reviewed:

- Cakici & Zaremba, *Getting the Target Right in Return Prediction* (SSRN 6615698, April 2026).

### External research check — direct ranking

Learning-to-rank research treats stock selection as an ordering problem and provides evidence that explicitly ranking assets can outperform regress-then-rank baselines in some settings. This does not require V4 to use LambdaMART or a listwise learner now; it validates the problem formulation while model-family choice remains V4-3 work.

Sources reviewed:

- Poh et al. (2020), arXiv:2012.07149.
- Lin, Su, Zhu, *Empirical Asset Pricing via Learning-to-Rank* (SSRN 6348379, 2026).

### H5/H10 choice — what is evidence versus product prior

The external literature supports fixed forward horizons, cross-sectional ranking, and the fact that horizon choice changes the forecasting problem.

It does **not** prove that H5 and H10 are universally optimal for IDX.

H5/H10 remain frozen because they are an outcome-blind product prior for an intended one-to-two-week swing window:

- H5 captures approximately one trading week;
- H10 captures approximately two trading weeks;
- using both prevents one arbitrary terminal endpoint from becoming the entire definition of opportunity;
- adding H3/H7/H20 after results would create rescue degrees of freedom.

Therefore H5/H10 are a deliberately chosen research definition, not a claim of historical optimality.

### Why separate fitted models remain correct

H5 and H10 are different supervised targets. Using the same initial pipeline but separately fitted artifacts isolates the effect of horizon while keeping the comparison interpretable.

A shared multi-output/multi-task learner may later be tested only as a separately preregistered challenger. It is not allowed to replace the independent baseline after results are seen.

### 50/50 consensus — what it means

The 50/50 H5/H10 consensus is a product prior, not an empirically optimized weight. Its purpose is to create one transparent shortlist score while retaining both component scores.

A future alternative weighting can only be a new preregistered challenger/generation.

### V4-1 red-team findings

The core target remains sound, with two implementation hazards now explicitly delegated to the V4-2 support gate:

1. historical `Open_(t+1)` is not defensibly observable for every row/date;
2. corporate actions or distinct trading mechanisms can break naive raw-price continuity.

These are data-admission problems, not reasons to reopen H5/H10 after outcome access.

### V4-1 final checkpoint verdict

`GO — KEEP LOCKED`.

Do not return to TP-first/SL-first, future MFE/max-price labels, risk-adjusted alpha labels, or a single H10-only target as a V4 rescue.

## V4-2 audit — evaluator

### Locked design after hardening

The primary evidence unit is the decision date.

H5, H10, and the 50/50 consensus are evaluated separately with:

1. daily cross-sectional Spearman IC;
2. fixed predicted Top-30 mean realized target percentile;
3. fixed predicted Top-30 minus Bottom-30 realized target spread;
4. mandatory raw-return diagnostics.

The initial historical-development structure is six expanding validation blocks of 100 signal sessions, with H10-governed purge and exact calendar/session identities frozen before outcomes.

### External research check — cross-sectional metrics

Cross-sectional forecast research evaluates whether forecasted rankings/cross-sectional dispersion align with realized returns and then studies prediction-sorted portfolios. Cross-sectional correlation is specifically used as a relative forecast-quality measure when exact return magnitude is not the only objective.

Sources reviewed:

- Gu, Kelly, Xiu (2020), prediction-sorted deciles.
- Han et al. (2024), cross-sectional forecast-performance measures.
- *Factor Timing with Portfolio Characteristics*, Review of Asset Pricing Studies 14(1), 2024, which explicitly discusses average cross-sectional correlation between forecasts and realized returns as a relative predictive-accuracy measure.
- Poh et al. (2020), ranking accuracy before portfolio construction.

The locked Top 30 is a product-level shortlist evaluator, not a portfolio-size optimization result.

### External research check — temporal leakage

H5/H10 labels from consecutive dates overlap. Standard IID cross-validation/inference would overstate effective sample size if overlapping label windows enter training/test incorrectly or if daily metrics are treated as independent.

The V4 evaluator therefore uses:

- chronological expanding validation;
- H10-governed purge;
- no random split;
- a moving date-block bootstrap with 10-session blocks for uncertainty.

Primary methodology source reviewed:

- Lazarev, *purgedcv: scikit-learn-compatible purged and combinatorial cross-validation for time-series and financial machine learning* (2026), which explicitly formalizes label-interval overlap and leakage-aware purging/embargo/walk-forward validation.

### New hardening added at this checkpoint

Three material evaluator guardrails were added before lock:

#### A. Target-observability gate

- horizon daily primary metric requires at least 90% target observability over the original EOD-scored decision population;
- consensus requires at least 90% both-target observability;
- predicted Top 30 is never refilled after the future is known;
- Top-30 primary metric requires at least 27/30 original predicted names to have the relevant defensible target.

This prevents future missingness from quietly redefining the decision population.

#### B. Price-continuity / trading-reference gate

Before V4 target materialization:

- no synthetic Open;
- no Close-t substitution;
- unresolved split/rights/stock-dividend/reverse-split continuity fails closed;
- unresolved `Open_(t+1)` semantics for a trading mechanism fails closed;
- Alpha target remains price return, not total shareholder return.

#### C. Dependence-aware uncertainty

Primary daily metrics use a fixed 10-session moving-block bootstrap, 2,000 repetitions, seed 42, 95% percentile interval, because H10 is the maximum frozen overlapping outcome window.

### Six-by-100 fold choice — what is evidence versus design prior

There is no universal theorem that six folds of exactly 100 sessions is optimal.

This is frozen as an outcome-blind validation design because it provides multiple chronological regimes, interpretable blocks, and substantial date-level validation coverage while keeping expanding training history.

If the support census shows the structure cannot be implemented under the already locked data gates, the experiment is blocked rather than silently redesigning folds after performance is known.

### V4-2 final checkpoint verdict

`GO — LOCKED WITH HARDENING`.

Locked checkpoint: `V4_2_DATE_CENTRIC_H5_H10_CONSENSUS_EVALUATOR_LOCKED_NO_MODEL_OR_OUTCOME_RUN`.

## Full V4-0 -> V4-2 adversarial checklist

| Threat | Status after checkpoint |
|---|---|
| signal uses EOD t but target pretends fill at Close t | CLOSED |
| future outcome determines whether alpha row existed | CLOSED at decision ledger; explicit target missingness remains visible |
| alpha mixes opportunity with Path Risk | CLOSED |
| alpha mixes sizing/execution | CLOSED |
| user forgot order is counted as alpha failure | CLOSED |
| non-fill is counted as alpha failure | CLOSED |
| one rigid H10 endpoint defines all swing opportunity | CLOSED by separate H5/H10 forecasts |
| future peak/MFE oracle exit | REJECTED |
| choose horizon after seeing backtest | REJECTED |
| choose H5/H10 weight after seeing backtest | REJECTED |
| use raw return magnitude as alpha's only task | REJECTED for initial V4; retained diagnostically/payoff layer |
| pooled rows dominate dates with larger universe | CLOSED by date-centric evidence |
| overlapping H10 labels leak across train/validation | CLOSED by H10 purge contract; exact boundaries still must be materialized |
| overlapping daily outcomes treated IID | CLOSED by 10-session block-bootstrap contract |
| missing Open silently drops hard rows | CLOSED by observability states/gates |
| Top 30 refilled after future target missingness is known | PROHIBITED |
| corporate action creates fake huge return | FAIL-CLOSED pending continuity resolver |
| alternate shortlist size chosen after result | PROHIBITED |
| historical 2021-2026 result called independent validation | PROHIBITED |
| old O2 forward counter reused as V4 validation | PROHIBITED |

## What is now frozen and cannot be edited as a rescue

### V4-0

- EOD-t decision timestamp;
- Alpha = relative opportunity ranker only;
- modular separation from risk/decision/sizing/execution;
- no `Close_t` pretend fill;
- explicit operational/execution/data states.

### V4-1

- `Open_(t+1)` research benchmark;
- H5 and H10 raw price-return horizons;
- within-date percentile-rank targets;
- two separately fitted models with the same initial pipeline policy;
- forecast horizon != mandatory exit;
- 50/50 H5/H10 consensus;
- no additional initial horizon.

### V4-2

- date-centric evidence;
- H5/H10/consensus evaluated separately;
- Spearman IC + fixed Top30 quality + Top30-Bottom30 spread;
- Top 30 only as primary shortlist;
- six expanding 100-session validation blocks;
- H10 purge;
- 90% target-observability date gate;
- 27/30 Top-30 observability gate;
- no Top-30 refill;
- 10-session moving-block bootstrap, 2,000 reps, seed 42;
- raw-return diagnostics mandatory;
- exact-common-support paired challenger comparisons;
- no Alpha-stage PnL/Sharpe/Kelly optimization;
- fresh prospective confirmation required after development.

## Remaining blockers before any historical V4 target/model run

This checkpoint does **not** authorize model training yet.

The next step must remain outcome-blind and must answer only whether the locked target is implementable on defensible historical support:

1. exact `Open_(t+1)` support census over the intended decision universe;
2. H5/H10 close maturity/support;
3. corporate-action price-continuity census under an admitted policy;
4. trading-mechanism/Open-reference semantics census;
5. target-state/missingness census by date and ticker;
6. exact six-by-100 fold boundary materialization and hash pinning;
7. confirmation that the 90% date gates and 27/30 Top-30 observability rule are technically feasible **without inspecting model performance**.

If these fail, the correct status is a data/target-support block. Do not alter V4-0/V4-1/V4-2 based on model outcomes because no model outcome should exist yet.

## Final preflight verdict

`V4_0_TO_V4_2_PREFLIGHT_GO_CONCEPTUAL_CONTRACTS_FROZEN_TARGET_MATERIALIZATION_REQUIRES_SUPPORT_CENSUS`

Interpretation:

> The conceptual direction is now strong enough to stop redesigning from intuition. V4-0, V4-1, and V4-2 are frozen. The next uncertainty is no longer "what should the model mean?" but "can the locked target be materialized cleanly enough on the historical data?" That question must be answered outcome-blind before V4-3 model-family/promotion work or any V4 performance run.

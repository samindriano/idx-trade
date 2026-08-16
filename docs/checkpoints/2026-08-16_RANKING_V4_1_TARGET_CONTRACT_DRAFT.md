# Ranking V4-1 — Target Contract Draft

Date: 2026-08-16 (Asia/Jakarta)  
Branch: `research/idx-ranking-v4-1-target-contract-v1`  
Parent V4-0 commit: `02716c29e6c41fe1f5244708f9cccac77d978eb9`  
Status: `V4_1_TARGET_CONTRACT_DRAFT_FOR_USER_REVIEW_NO_OUTCOME_RUN`

## Scope

This checkpoint proposes the economic target for Alpha V4 under the already locked V4-0 architecture.

It is outcome-blind design only. No historical V4 labels are materialized, no historical outcome is inspected, no model is fit, no feature is selected, no metric is run, no protected forward outcome is accessed, and no old V1/V2/V3/O2 result is used to choose among target variants by performance.

The target must respect V4-0:

- Alpha V4 is an opportunity ranker only;
- scoring occurs after validated EOD session `t`;
- no post-signal `Close_t` pseudo-fill;
- risk/path, trade decision, sizing and execution remain separate layers;
- future market unavailability, execution non-fill, operational miss and research missingness are distinct states.

## 1. What Alpha V4 should rank

The proposed Alpha V4 question is:

> Among securities scored after EOD session `t`, which securities subsequently deliver the strongest **relative price appreciation** over a fixed swing horizon beginning from the earliest defensible next-session price benchmark?

This intentionally does not ask:

- whether the trade should actually be taken;
- how risky the path will be;
- how much capital should be allocated;
- which limit price should be used;
- whether an actual order would fill;
- what the calibrated expected percentage payoff is.

Those remain downstream questions.

## 2. Candidate target families considered outcome-blind

### A. Legacy resolved TP-first versus SL-first binary target

**Reject as V4 primary.**

Reason:

- future barrier resolution determines whether a row enters the binary population;
- no-hit/quiet cases disappear;
- target mixes directional opportunity with a fixed risk/barrier geometry;
- it inherits the core V1->O2 estimand problem.

Barrier outcomes can remain later diagnostics or decision-layer research, but not the primary Alpha V4 target.

### B. Maximum favorable excursion / best price reached inside the horizon

**Reject as V4 primary.**

Reason:

- rewards an oracle-like best exit that the system did not know in advance;
- can score a stock highly even if the gain existed only briefly and later disappeared;
- overlaps future path/exit-policy research;
- is better treated as auxiliary path/payoff evidence than the alpha ordering target.

### C. Risk-adjusted composite utility such as upside minus drawdown penalty

**Reject as V4 primary.**

Reason:

- directly mixes alpha with Path Risk;
- requires an arbitrary risk-aversion coefficient;
- makes later attribution difficult;
- violates the modular V4-0 boundary.

A future Decision Engine may combine independently validated alpha and risk evidence under its own frozen policy.

### D. Fixed-horizon forward price return

**Retain as the preferred economic outcome.**

Advantages:

- every ordinary observed price path produces a value; no `NO_HIT` deletion;
- no ATR barrier or directional threshold is required;
- no path-risk penalty is embedded;
- no oracle best exit is assumed;
- entry reference can begin strictly after the EOD signal;
- simple, interpretable and compatible with a later ranking objective.

### E. Same-date cross-sectional rank of the fixed-horizon forward return

**Retain as the preferred Alpha V4 relevance semantics.**

Alpha is explicitly a relative opportunity ranker, not a return-calibration model. Therefore the canonical continuous outcome should be preserved, while the alpha target meaning is the same-date ordering of that outcome.

This also keeps a clean conceptual separation from a future Expected Payoff model:

- **Alpha:** which stock is better relative to contemporaneous alternatives?
- **Expected Payoff:** what return magnitude/distribution should be expected?

## 3. Proposed primary horizon

Primary proposal: **H10 = ten official IDX trading sessions of holding exposure beginning at session `t+1`.**

Definitions:

- `t`: EOD signal session;
- `s1`: next official IDX session after `t` (`t+1` in session time);
- `s10`: tenth official IDX session after `t`, with `s1` counted as holding day 1;
- entry benchmark: certified regular-market `Open_(s1)`;
- terminal benchmark: certified regular-market `Close_(s10)`.

Why H10 is proposed:

- it encodes the intended swing rather than intraday use case;
- approximately two trading weeks is long enough to be distinct from short-term execution noise while still being operationally swing-oriented;
- H10 is selected here as a product-horizon convention, **not** because historical V1/V2/V3/O2 performance was better at H10.

No H5/H20 challenger is authorized by this draft. If horizon sensitivity is desired later, it must be frozen as a non-selection diagnostic before outcomes are materialized; the primary horizon must not be selected by whichever historical horizon performs best.

## 4. Proposed canonical continuous outcome

For security `i` scored at decision session `t`:

```text
forward_price_return_h10(i,t)
    = Close(i,s10) / Open(i,s1) - 1
```

where `s1` and `s10` are defined above.

Simple return is preferred over log return for interpretability. They induce the same within-date ordering when both prices are positive, so this choice is not intended as a model-performance degree of freedom.

This is explicitly a **price-return** target, not total shareholder return, transaction-cost-adjusted return or realized portfolio PnL.

## 5. Proposed Alpha relevance target

For every decision date `t`, among securities whose canonical H10 return is defensibly observable under the target-state contract:

```text
alpha_relevance_rank(i,t)
    = within-date percentile rank of forward_price_return_h10(i,t)
```

Higher is better.

Important interpretation:

- if the entire market falls, the #1 stock can still have a negative absolute H10 return;
- if the entire market rises, a lower-ranked stock can still have a positive absolute return.

That is intentional. Alpha V4 answers **relative opportunity**, while the Decision Engine later decides whether absolute conditions justify taking any trade at all.

The raw `forward_price_return_h10` must always be preserved alongside the rank target for auditability and future payoff research. The rank transformation must not destroy the continuous outcome artifact.

## 6. Why the target begins at `Open_(t+1)`

The EOD `t` signal is not known early enough to claim an executable `Close_t` entry. Therefore Alpha V4 must not receive credit for an overnight move that happened before the next-session entry benchmark.

Example:

```text
Close_t           1,000
Open_(t+1)        1,100
Close_(t+10)      1,155
```

The V4 alpha outcome is approximately `+5%`, not `+15.5%`.

The +10% overnight gap occurred before the proposed next-session entry benchmark and is therefore not captured as post-signal alpha.

`Open_(t+1)` remains a **research benchmark**, not an assertion that the user's actual limit order filled exactly at the official Open. Actual fill/non-fill, partial fill and slippage remain Execution-layer responsibilities under V4-0.

## 7. No risk/path information inside the Alpha target

The primary target intentionally does not include:

- maximum adverse excursion;
- maximum drawdown;
- volatility penalty;
- stop-loss touch;
- ATR-normalized loss;
- probability of ruin;
- Path Risk output;
- position-size penalty.

Those dimensions may be important to deciding whether to trade or how much to size, but embedding them in the alpha target would make it impossible to distinguish:

> `low opportunity`

from

> `high opportunity but high path risk`.

The project explicitly wants those to remain separate states.

## 8. No execution/cost information inside the Alpha target

The target also excludes:

- limit-order choice;
- actual broker fill;
- execution probability;
- spread;
- slippage;
- brokerage fees;
- queue priority;
- user forgetting to place an order.

These belong to downstream execution/paper/live layers.

A stock can be correctly ranked as a strong Alpha V4 opportunity even if a later execution policy does not fill it.

## 9. Decision-time population versus target states

Every security/session admitted to the Alpha V4 scoring universe at EOD `t` remains a recorded decision row.

Future events may determine **target state**, but may not erase the original alpha decision row.

Each row must receive exactly one target-state classification before model/evaluator use.

Proposed minimum target states:

### `RETURN_OBSERVED`

Requirements include:

- valid decision-time row at EOD `t`;
- next official session identified;
- certified entry benchmark at `Open_(s1)`;
- certified terminal benchmark at `Close_(s10)`;
- no unresolved price-continuity event that makes the raw price ratio economically meaningless.

Only this state has a numeric `forward_price_return_h10` and within-date alpha relevance rank.

### `MARKET_ENTRY_UNAVAILABLE`

The market/security genuinely prevented the frozen entry benchmark from existing under the market-state contract.

This is **not** an Alpha prediction failure and must remain counted/reported in the decision ledger.

### `ENTRY_DATA_UNOBSERVABLE`

The market event may have existed, but research data cannot defensibly observe the required `Open_(s1)`.

This is data missingness, not market unavailability.

### `HORIZON_MARKET_INTERRUPTED`

Entry benchmark exists, but a later market/security event prevents the frozen terminal benchmark from being economically defined under the target contract.

Do not silently substitute a stale last price.

### `HORIZON_DATA_UNOBSERVABLE`

The terminal market event may have existed but the research corpus cannot defensibly observe the required `Close_(s10)`.

### `PRICE_CONTINUITY_UNRESOLVED`

A split/reverse-split or other mechanical share-price rescaling within the target window cannot be reconciled under an admitted corporate-action/price-continuity contract.

Do not create a false large return from mechanically incompatible raw prices.

The exact engineering decision tree for these states belongs to implementation after the target is locked.

## 10. Conditioning rule for Alpha research

Alpha performance on the numeric return target is evaluated on `RETURN_OBSERVED` rows only, because other states do not possess a defensible numeric return under this target.

However this conditioning must be explicit and fully reported:

- decision-time row count;
- `RETURN_OBSERVED` count/rate;
- each non-observed target-state count/rate by date/era/ticker strata;
- no silent deletion;
- no inference that market/data unavailability equals bad alpha.

This differs materially from the old resolved-only target: ordinary no-move, sideways and poor-return price paths remain numeric observed outcomes and stay in the Alpha target population.

## 11. Corporate-action scope

The proposed Alpha V4 target is a raw execution-price **price return**, not total shareholder return.

Cash distributions are not added to the target. This preserves a simple price-opportunity question for a swing ranker.

Mechanical share-price rescalings such as stock splits/reverse splits must not be allowed to create artificial returns. If continuity cannot be defensibly reconciled, the target state must fail closed as `PRICE_CONTINUITY_UNRESOLVED` rather than invent an adjustment.

This contract does not authorize a new corporate-action backfill or provider rescue.

## 12. What this target deliberately gives up

A fixed terminal H10 return does not give the alpha model credit for an unexecuted perfect exit inside the horizon.

Example:

```text
Open_(t+1)        1,000
Day 4 high        1,200
Close_(t+10)      1,030
```

Primary Alpha V4 outcome: `+3%`, not `+20%`.

That is intentional. The alpha target must not use hindsight to assume the trader sold at the best future price. Path/payoff/exit-policy research can separately characterize the richer path later.

## 13. Relationship to Path Risk and Expected Payoff

### Alpha V4

Ranks relative H10 price appreciation.

### Path Risk

Characterizes adverse future path separately, potentially with richer intraday information when admitted.

### Expected Payoff

If revisited in a new lineage, estimates magnitude/distribution rather than merely relative rank. The historical Expected Payoff V1 failure remains closed and is not rescued by V4-1.

### Decision Engine

Eventually combines independently validated outputs to choose trade versus skip.

Thus a future state may look conceptually like:

```text
Ticker             ABCD
Alpha percentile     96
Expected payoff      +?      [separate model]
Path Risk            ?       [separate model]
Reliability          ?       [separate model/sidecar]
Decision             not defined by V4-1
```

## 14. Why not make Alpha target absolute profitability

The alpha ranker is cross-sectional by design.

On a severe down-market day, the best stock may still have a negative H10 return. Alpha should be allowed to say "this is the least-bad / relatively strongest opportunity" without being forced to decide that it should be traded.

The later Decision Engine can use market state, payoff, risk, execution conditions and portfolio constraints to choose `NO TRADE` even when Alpha has a valid #1 ranking.

This separation prevents the alpha label from becoming an all-in-one trading utility.

## 15. Items deliberately deferred to V4-2 / V4-3

This draft does not choose:

- primary ranking metric;
- top-N or quantile evaluation rule;
- equal-date weighting implementation;
- promotion thresholds;
- fold boundaries;
- HGB versus CatBoost versus ranking-native learner;
- exact feature set;
- whether training uses the numeric return, percentile relevance, pairwise comparisons or a grouped ranking loss;
- any feature block such as Structure, Open geometry, Foreign Flow, fundamentals or intraday.

V4-2 should freeze the date-centric evaluator and promotion governance.
V4-3 should then define the minimal baseline candidate family.

## 16. Proposed V4-1 lock statement

If approved, freeze:

> After validated EOD session `t`, Alpha V4's canonical economic outcome is the raw price return from the certified regular-market `Open` of the next official IDX session to the certified regular-market `Close` of the tenth official IDX session after `t`, with the next session counted as holding day 1. Alpha relevance is the same-decision-date cross-sectional ordering/percentile rank of that H10 forward price return. All ordinary observed paths, including negative, flat and no-hit paths, remain numeric target observations. Path risk, expected payoff calibration, trade/no-trade decisions, sizing, transaction costs and actual fill mechanics are excluded from the Alpha target. Future market/data/continuity failures are explicit target states and may not erase the original EOD decision row.

Proposed verdict after user approval:

`V4_1_TARGET_CONTRACT_LOCKED_H10_NEXT_OPEN_TO_H10_CLOSE_CROSS_SECTIONAL_RETURN_RANK`

Until approval:

`V4_1_TARGET_CONTRACT_DRAFT_FOR_USER_REVIEW_NO_OUTCOME_RUN`

## Stop rule

Do not materialize V4 labels, run outcome distributions, compare H5/H10/H20, fit any V4 model, inspect protected forward outcomes, or tune this target based on historical performance before the user reviews/approves the contract.
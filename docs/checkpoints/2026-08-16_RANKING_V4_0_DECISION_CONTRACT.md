# Ranking V4-0 — Decision and System Boundary Contract

Date: 2026-08-16 (Asia/Jakarta)  
Branch: `research/idx-ranking-v4-0-decision-contract-v1`  
Parent forensic synthesis: `be0dc9e1175568a717c54b9ee7402f34c0252724`  
Status: `V4_0_DECISION_CONTRACT_LOCKED_NO_TARGET_MODEL_OR_OUTCOME_RUN`

## Purpose

V4-0 freezes the decision timestamp and architectural responsibility of the next alpha generation before any target, model, feature family, or historical outcome is chosen.

It exists because the V1 -> V2 -> V3 -> O2 forensic synthesis found that representation improved while the old research lineage retained two foundation-level problems: future-conditioned resolved-only target membership and a `Close_t` outcome reference even though the signal is only known after session `t` closes.

V4-0 does not select a replacement target. That belongs to V4-1.

## Locked product role of Alpha V4

Alpha V4 is an **opportunity ranker only**.

After the official EOD state for session `t` is available and validated, Alpha V4 scores/ranks the decision-time eligible IDX universe using only information known by that cutoff.

Its question is:

> Among the opportunities that can be evaluated after session `t` ends, which securities appear relatively more attractive for a future swing-long opportunity?

Alpha V4 does **not** itself decide whether the user should trade, how much capital to allocate, which limit price to submit, or whether an order will fill.

## Locked timing contract

1. Information cutoff: after official EOD session `t` is available and validated.
2. Alpha ranking may be generated during the afternoon/evening after EOD.
3. Any real trade action must occur strictly after the alpha ranking exists.
4. No V4 target may use `Close_t` as a pretend post-signal executable fill.
5. The earliest future market state relevant to an executable research target begins on official session `t+1`.
6. Exact V4-1 outcome/reference semantics are intentionally not selected here.

This design supports a practical workflow in which the system finishes scoring after EOD, produces a trade plan before the next session, and allows orders to be prepared in advance rather than requiring the user to wake up at the market open.

## Locked modular architecture

The system must preserve separate responsibilities:

```text
Data / Universe Gate
        ↓
Alpha / Opportunity Ranker
        ↓
Secondary evidence
  ├─ Path Risk
  ├─ Probability / payoff, if separately validated
  └─ Reliability / uncertainty, if separately validated
        ↓
Decision / Trade Selection Engine
        ↓
Portfolio / Position Sizing
        ↓
Execution / Order and Fill Model
        ↓
Paper / Shadow Ledger + Real Ledger
```

The architectural rule remains:

`Opportunity != Path Risk != Probability != Payoff != Decision != Sizing != Execution`

The project must not replace these distinctions with one opaque all-in-one model unless a future separately preregistered research program establishes a clear scientific reason to do so.

## Responsibility boundaries

### Alpha / Opportunity Ranker

Responsible for:

- relative opportunity ranking;
- strictly point-in-time features available by EOD `t`;
- cross-sectional opportunity ordering.

Not responsible for:

- BUY/SELL/no-trade decision;
- final risk acceptance;
- position size;
- portfolio exposure;
- limit-order price;
- fill probability;
- spread/slippage/fees;
- operational user behavior.

### Path Risk

A separate model/research layer responsible for future adverse-path characterization. Intraday data acquisition may improve this layer, but no intraday source is automatically admitted into Alpha V4.

Path Risk does not automatically filter alpha ranks. Any `risk -> reject/size` mapping belongs to the Decision/Portfolio layers and requires its own frozen validation.

### Decision / Trade Selection

Combines only evidence that has earned its own admission/validation status, plus explicitly defined operational constraints, to decide trade versus skip.

It must not be invented by post-hoc searching for whichever historical combination of alpha/risk/payoff looks best.

### Portfolio / Sizing

Responsible for capital allocation, risk budgets, concentration, maximum positions, diversification and eventual sizing rules.

Sizing is explicitly outside the Alpha V4 target.

### Execution

Responsible for translating a selected trade into an order policy and modeling realistic market mechanics, including:

- limit price;
- order timing;
- fill/non-fill;
- partial fill;
- spread;
- slippage;
- fees;
- liquidity/capacity;
- broker/market execution semantics.

An official `Open_(t+1)` value is not automatically equal to the user's actual fill price.

## Distinguish four different failure states

The following cases must never be conflated:

1. `MARKET_ENTRY_UNAVAILABLE` — the market/security genuinely cannot be entered under the frozen market contract (for example a relevant suspension/tradability state).
2. `EXECUTION_NON_FILL` — a valid order was submitted but did not fill under the execution policy, for example because the limit price was not reached/matched.
3. `OPERATIONAL_MISS` — the user/system failed to submit the intended order despite a valid trade plan, for example forgetting to place the order.
4. `RESEARCH_DATA_UNOBSERVABLE` — the relevant market event may have existed but the research dataset cannot defensibly observe it.

None of these states may be silently removed from downstream evaluation or relabeled as an Alpha V4 prediction failure.

## Paper / Shadow trading is a first-class future layer

The mature system should maintain an automated deterministic paper/shadow ledger alongside the real portfolio ledger.

Purpose:

- preserve what the validated decision/execution policy would have done;
- distinguish model/system quality from manual-user execution differences;
- avoid contaminating model assessment when the user forgets an order, is unavailable, or intentionally deviates;
- provide a deployment bridge before any real automated execution.

Conceptually:

```text
Validated model outputs
        ↓
Decision + sizing + execution policy
        ↓
Automated Paper / Shadow Portfolio

Actual human/broker actions
        ↓
Real Portfolio Ledger

Paper vs Real divergence
        ↓
Operational / execution attribution
```

Paper trading is not authorization for live order routing.

## Decision-time population rule

The alpha scoring population must be determined from information available by the EOD `t` cutoff.

A future event must not retroactively decide whether a decision-time alpha row existed.

Therefore later suspension, non-fill, no-move, target no-hit, or other outcome states must be represented explicitly by the relevant downstream target/evaluator rather than silently deleting the original decision.

Exact eligibility and outcome-state semantics remain V4-1/V4-2 work.

## What V4-0 deliberately does NOT decide

V4-0 does not freeze:

- H5/H10/H20 or any other holding horizon;
- barrier versus continuous versus ordinal/path target;
- `Open_(t+1)` versus another defensible future benchmark as the exact Alpha V4 target reference;
- target utility formula;
- ATR multipliers;
- transaction-cost assumptions;
- top-N selection rules;
- HGB/CatBoost/LambdaMART/other learners;
- exact V2 feature inheritance;
- Structure-Lite inclusion;
- Open/session-geometry inclusion;
- Foreign Flow, financial, ownership, sector or intraday inclusion;
- decision thresholds;
- sizing rules;
- execution limit-price rules.

Those choices must not be inferred from old consumed outcomes.

## Relationship to legacy Clean V2 and O2

Clean V2 `HGB_XS_MARKET` remains the current historical contextual benchmark under the **old target contract**.

V4-0 does not promote or demote it based on new outcomes. It also does not inherit the old resolved-only H10 label or `Close_t` economic reference.

V3-B Structure-Lite and O2 completed-session geometry remain candidate information hypotheses only. They do not enter V4 automatically.

The legacy O2 forward/shadow infrastructure is a separate protected lineage and cannot serve automatically as independent validation for V4 because V4 changes the research question.

## Research-governance lock

Before V4-1 is frozen:

- no new historical V4 outcome run;
- no target comparison using consumed outcomes;
- no model fit;
- no feature search;
- no Structure x Open rescue experiment;
- no tuning of horizon/barrier/utility based on historical performance;
- no protected forward-outcome access.

V4-1 may compare target families **conceptually and mechanically** before selecting one frozen primary target contract.

## Final locked statement

> After official EOD session `t`, Alpha V4 ranks the decision-time eligible IDX universe by relative future swing-long opportunity using only information known by that cutoff. It is an opportunity-ranking layer, not a trade-decision, risk, sizing, or execution model. Any real action occurs strictly after the ranking exists; `Close_t` may not be treated as a post-signal fill. Market entry unavailability, execution non-fill, operational miss, and research-data missingness are distinct downstream states. Path Risk, decision, sizing, execution, and paper/shadow portfolio accounting remain separate modules with separate research contracts.

Verdict:

`V4_0_DECISION_CONTRACT_LOCKED_NO_TARGET_MODEL_OR_OUTCOME_RUN`

Next authorized design stage: **V4-1 Target Contract Design**, initially outcome-blind.
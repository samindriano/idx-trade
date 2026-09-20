# IDX-Trade — Risk, Concentration, and Holding-Dynamics Audit V1

Date: 2026-09-20 (Asia/Jakarta)

Status: `READ-ONLY STRUCTURAL AUDIT / RISK OVERLAY NOT CERTIFIED`

This is a new system-wide deep-dive result, not a new alpha experiment. It
audits the retained pinned runtime and prior structural evidence. No protected
outcome, provider, cloud, capture, canonical dataset, production state, or
incumbent state was accessed or changed.

## 1. Evidence and exact boundary

Primary runtime snapshot:

`045e25a19d9f71170d2c863e768102937e59ad73`

Relevant files:

- `src/idx_trade/v4_x1_decision_v2_minimal.py`
- `src/idx_trade/v4_x1_sizing_v1.py`
- `src/idx_trade/v4_x1_execution_v1.py`
- `config/v4_x1_sizing_v1.json`
- `config/v4_x1_execution_v1.json`
- `docs/checkpoints/2026-08-21_V4_X1_DECISION_V1_STRUCTURAL_TRAJECTORY_RESULT.md`
- `docs/checkpoints/2026-08-21_V4_X1_DECISION_V1_TEMPORAL_PERSISTENCE_DIAGNOSIS_RESULT.md`
- `docs/checkpoints/2026-08-21_V4_X1_SIZING_EXECUTION_V1_HARD_AUDIT_REMEDIATION.md`

This audit intentionally does not infer live risk behavior from a model return
series or hidden PnL. All conclusions are contract/static or synthetic.

## 2. Main finding

The current system has bounded entry-sizing and execution guards, but it does
not have an active portfolio-risk layer. Risk control is therefore narrower
than the name “portfolio system” may suggest.

The enforced layer is approximately:

`Decision top-10 and state transitions -> equal-quota sizing -> 15% per-entry
cap -> cash/lot/fee/capacity checks -> paper execution`

The following are not active controls in the pinned configuration:

- drawdown or loss-triggered de-risking;
- total portfolio exposure cap other than the implicit number of seats/cash;
- sector or industry concentration cap;
- issuer-group or correlated-name concentration cap;
- beta/market-factor exposure cap;
- volatility target or volatility scaling;
- stop-loss or emergency risk exit;
- post-entry weight trimming/rebalancing;
- strategic cash overlay.

This is not automatically a defect if deliberately out of scope, but it is a
material hidden assumption: the system is a fixed-seat, equal-quota paper
allocator, not a complete risk-managed portfolio engine.

## 3. Direct static evidence

### 3.1 Decision profile is rank/state control, not risk control

The pinned Decision V2 profile uses:

- target count maximum: 10;
- strong zone maximum rank: 10;
- retention zone maximum rank: 20;
- soft replacement rank advantage: 5;
- previous-rank entry confirmation maximum: 20.

These settings govern membership persistence and replacement. They do not
measure portfolio exposure, issuer correlation, sector concentration, drawdown,
or factor risk.

### 3.2 Sizing is fixed equal-quota with a per-name entry cap

`v4_x1_sizing_v1.py` and its config declare:

- `TARGET_WEIGHT_PER_NAME = 0.10`;
- `MAX_ENTRY_WEIGHT_PER_NAME = 0.15`;
- `rank_weighting = false`;
- `conviction_weighting = false`;
- `strategic_cash_overlay = false`;
- residual cash allowed for lot rounding, fees, and execution constraints.

The allocation method is
`EQUAL_QUOTA_FLOOR_PLUS_ONE_LOT_RESIDUAL_ENUMERATION` and the objective uses
rank only as the specified tie-break/ordering, not as a risk-weighted
conviction signal.

The 15% cap is an entry cap. It is not a continuing mark-to-market portfolio
weight cap.

### 3.3 Execution explicitly defers post-entry risk controls

`config/v4_x1_execution_v1.json` declares:

`post_entry_weight_drift_policy = NO_COSMETIC_REBALANCE_PORTFOLIO_RISK_OVERLAY_FUTURE`

The same config marks the strategic cash overlay false. A source scan of the
pinned `src/**` tree found risk-related configuration only for the strategic
cash flag; no active drawdown, sector-cap, concentration-cap, or portfolio-risk
overlay implementation was found.

This means price drift can change actual weights after entry without an active
risk rebalance rule.

### 3.4 Existing guards are still valuable but narrower

The engine does enforce or validate important local invariants:

- non-negative cash;
- whole-lot shares;
- per-entry maximum weight;
- cash and fee affordability;
- regular-market-value capacity reference;
- sell-before-buy ordering in the execution path;
- CA evidence and unresolved-CA fail-closed behavior;
- pending sell handling for zero/partial exit capacity;
- deterministic tie-breaking under the declared allocation objective.

Those are execution/accounting safety guards. They are not substitutes for a
portfolio-level risk budget.

## 4. Historical / prior evidence that changes interpretation

### 4.1 Decision V1 turnover was near daily Top-10 behavior

The prior structural trajectory audit reported naive turnover ratio
`0.8589702590` and found that the rank>20 hard-exit boundary dominated turnover.
The policy behaved much closer to daily exact Top-10 than intended as a sticky
policy.

This matters for risk because high replacement frequency increases realized
cost, capacity demand, and the number of times the portfolio is exposed to the
entry/exit assumptions.

### 4.2 Persistence improves stability but can create capacity shortages

The prior temporal-persistence diagnosis found persistence materially
discriminative, but a strict persistent-only 10-name portfolio often lacks ten
qualified names. A system that insists on full replenishment can therefore
convert a stability filter into a capacity or concentration problem.

The retained decision design correctly allows unfilled slots rather than
forcing arbitrary names. That preserves scientific semantics but leaves an
explicit exposure/cash state that must be risk-accounted for.

### 4.3 Prior sizing remediation intentionally left risk overlays future

The historical sizing/execution hard-audit remediation fixed major local bugs:

- per-entry cash drag from independent budgets;
- low-price fee pressure;
- pending retry semantics for blocked/partial transitions;
- partial-exit capacity;
- paired sell dependency;
- CA boolean rejection;
- forged DecisionPlan rejection;
- capacity and provenance guards.

It also explicitly retained “no strategic market-timing cash overlay” and
“post-entry weight drift is not cosmetically trimmed”; portfolio
concentration/market-risk overlays were left as a future separate layer.

That was an intentional boundary, not evidence that the missing layer is safe.

## 5. System interactions and hidden assumptions

### 5.1 Equal quota does not imply equal risk

Ten names at 10% each can have substantially different beta, volatility,
liquidity, sector, issuer, or common-factor exposure. The current sizing
contract controls nominal allocation, not risk contribution.

### 5.2 Entry cap does not bound future concentration

A name entered at 10% or 15% can become a larger portfolio weight after other
names are sold, after partial exits, or after price movement. Since post-entry
drift is not actively trimmed, the entry cap is not a continuing concentration
bound.

### 5.3 Empty seats and residual cash are coupled states

When Decision V2 has unfilled slots, or when capacity/lot size prevents a full
allocation, the portfolio can hold cash above the nominal 10-seat design. That
is correct under the declared no-renormalization rule, but the state needs to be
distinguished between:

- intentional no-qualified-challenger cash;
- data/Open unavailable cash;
- capacity-limited cash;
- lot/fee infeasibility cash;
- pending-order cash;
- risk-overlay cash, if a future overlay exists.

Without this classification, lower exposure can be misread as either safe
de-risking or an execution failure.

### 5.4 Turnover and risk are not independent

Decision churn creates more executions, more fee/slippage exposure, and more
opportunities for capacity constraints. Conversely, capacity constraints create
pending orders and stale holdings, which can alter concentration and reduce the
intended Decision exposure. The present components handle pieces of this loop,
but there is no single portfolio-level invariant covering it.

### 5.5 CA and risk state interact

CA projection can change cash/NAV and therefore sizing. The earlier lineage audit
found that the recorded CA hash can describe the pre-projection state while
sizing consumed the projected state. Until this is fixed, a risk or exposure
report built from the recorded hash could be describing a different state than
the allocator used.

## 6. Structural counterexamples to test next

These are proposed synthetic tests, not executed live trades:

1. **Price winner drift:** enter ten names at 10%; multiply one price by 3x,
   sell two other names, and verify whether any active invariant prevents the
   winner from exceeding an intended concentration limit.
2. **Correlated basket:** ten names each at 10% from one synthetic sector/factor;
   verify that nominal sizing passes while factor exposure remains unbounded.
3. **Unfilled-seat transition:** Decision returns six qualified names for three
   sessions, then ten; distinguish intentional cash from capacity and pending
   states across restart.
4. **Partial-fill plus replacement:** partially fill a buy, then receive a
   replacement sell on the next session; verify residual intent, cash reserve,
   and no duplicate exposure.
5. **CA cash shock:** project a dividend/CA state that changes available NAV,
   then verify the risk report, sizing input, and persisted hash all refer to
   the same projected state.
6. **Restart during risk decision:** interrupt after execution but before any
   future overlay decision; verify that a restart cannot silently apply a
   different concentration policy.

## 7. Verdict and required future hardening

Verdict:

`RISK_OVERLAY_NOT_CERTIFIED / LOCAL ACCOUNTING GUARDS PASS BOUNDED`

The smallest high-value hardening sequence is:

1. define whether the system intentionally has no portfolio-risk overlay or
   requires one for paper admissibility;
2. add a typed exposure-state taxonomy for empty seats, cash, pending orders,
   and capacity limitations;
3. define continuing versus entry-only weight limits;
4. add synthetic concentration/factor/price-drift invariants;
5. bind any risk decision to the exact projected CA/NAV state and runtime config;
6. only then consider an implementation, without reopening frozen Decision V2
   research or protected outcomes.

No retry, model sweep, provider call, or production mutation was performed.


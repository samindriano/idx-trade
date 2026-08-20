# V4-X1 Decision V1 — Sizing V1 Freeze and Core Implementation

Date: 2026-08-21
Branch: `research/idx-v4-x1-decision-v1`

## Verdict

`SIZING_V1_CORE_IMPLEMENTED_PRE_EXECUTION_CONTRACT_NO_HISTORICAL_PNL`

Sizing V1 is frozen as the simple executable-paper baseline downstream of frozen V4-X1 Alpha and Decision V1. It does not change alpha ranking, Decision V1 membership, or holding/exit semantics.

## Frozen sizing policy

- Primary executable paper NAV: `Rp50,000,000`
- Sensitivity NAVs: `Rp25,000,000` and `Rp100,000,000`
- Feasibility-only NAV: `Rp10,000,000`
- IDX lot size: `100 shares`
- Economic target: approximately equal `10% NAV` per new Decision V1 name
- Entry cap at sizing reference: `15% NAV` per new name
- Rank weighting: forbidden in V1
- Conviction weighting: forbidden in V1
- Daily cosmetic rebalancing of HOLD names: forbidden
- Strategic cash / market-timing overlay: forbidden in V1
- Residual cash from lot granularity, infeasibility, fees, or execution mechanics: allowed
- Future risk-off lane: `MARKET_EXPOSURE_OVERLAY_V1`, separate challenger only

## Equal-quota lot allocator

For a batch of BUY intents:

1. compute equal per-entry quota:
   `min(10% * current NAV, available_cash / number_of_entries)`;
2. for each name, compute feasible whole-lot floor quota subject to the 15% entry cap;
3. never reduce a feasible name below its equal-quota floor merely to finance another name;
4. residual cash may fund at most the one-lot rounding upgrade around each quota;
5. enumerate the floor/one-lot-upgrade combinations exactly and choose minimum normalized squared quota error;
6. on exact mathematical ties, invest more; final deterministic tie-break uses ticker ASC, never rank.

This is intentionally not a global portfolio optimizer. The goal is a clean equal-ish baseline without hidden rank conviction or cross-subsidizing one selected name by severely underfunding another.

## Layer boundary

Sizing V1 consumes only Decision V1 BUY intents and a caller-supplied pre-trade reference-price map plus current NAV / available cash.

It does **not** decide:
- which names belong in the portfolio;
- whether to hold strategic cash;
- realized fills;
- exact Open(t+1) fill mechanics;
- fees;
- slippage;
- settlement / sale-proceeds availability.

Exact price-timing and fill semantics are deferred to `Execution V1`.

Importantly, Sizing V1 must not determine lots using the realized Open(t+1) and then pretend the same order was already executable at that Open. Historical PnL remains unauthorized until the execution contract removes that look-ahead ambiguity.

## Validation

Local pre-publish validation:

- focused sizing tests: `16 passed`
- randomized adversarial sizing cases: `30,000 passed`
- tested invariants:
  - total sized notional never exceeds supplied available cash;
  - all quantities are multiples of 100 shares;
  - new-entry reference weight never exceeds 15%;
  - no daily sizing action when there are no BUY intents;
  - rank labels do not alter equal-quota lot allocation;
  - input order does not alter allocation;
  - one-lot infeasibility is fail-closed and explicit;
  - equal-quota floor cannot be sacrificed to fund another selected name.

## Next action

Freeze and implement `Execution V1` before any historical PnL:

- exact pre-trade sizing reference available at EOD(t);
- Open(t+1) / at-or-after-open fill convention;
- sell-before-buy / buying-power semantics for paired replacements;
- non-fill / suspension behavior;
- fee assumptions;
- slippage / spread assumptions;
- immutable paper ledger transition rules.

Historical PnL remains locked until those rules are preregistered.

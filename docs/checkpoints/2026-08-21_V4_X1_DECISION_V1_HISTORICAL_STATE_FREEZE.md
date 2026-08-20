# V4-X1 Decision V1 — Historical State Freeze

Date: 2026-08-21 Asia/Jakarta
Branch: `research/idx-v4-x1-decision-v1`
Status: `FROZEN_PRE_SIZING_AND_HISTORICAL_PNL`

## Frozen state semantics

Decision V1 starts the historical OOS trajectory once, from `EMPTY_POSITIONS_ALL_CASH`, on the first of the exact frozen 600 V4-X1 OOS score dates. There is no pre-roll. The first decision selects the Decision V1 target set from that first OOS score artifact; earliest execution remains official Open(t+1).

The Decision V1 shadow state then carries continuously across all 600 OOS dates and across all six 100-date fold boundaries. Fold boundaries are alpha model evaluation boundaries, not economic liquidation events. There is no fold-boundary portfolio reset or forced liquidation.

## Cash semantics clarification

The earlier shorthand `always invested` must not be interpreted as literal 100% NAV investment.

The frozen meaning is:

- no discretionary market-timing/risk-off cash rule in Decision V1;
- Decision V1 targets 10 security names when a complete verified ranking permits it;
- actual invested NAV may be below 100%;
- residual cash is explicitly allowed because IDX trades in integer lots and because future sizing/execution may create rounding, fee, partial-fill, or other execution residuals;
- the exact cash amount, share/lot quantities, and capital allocation are not Decision V1 responsibilities and remain deferred to the separately frozen sizing/execution contract.

Therefore `target_positions=10` is a security-selection target, not a requirement that portfolio cash equal zero.

## Historical evaluation boundary

Historical PnL is **not yet authorized**. Position quantities, lot rounding, initial capital, weight allocation, fees, and fill assumptions must be frozen before a portfolio-return backtest is run.

The accepted V4-X1 alpha evidence remains unchanged and the alpha model/folds are not reopened.

Verdict:

`DECISION_V1_STATE_CONTINUOUS_600_OOS_EMPTY_START_RESIDUAL_CASH_ALLOWED_PNL_NOT_YET_AUTHORIZED`

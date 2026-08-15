# Handoff — Price / Trend / Confirmation State V1

from: ChatGPT
to: Codex local runtime / ChatGPT independent review
task_id: IDX-PRICE-TREND-CONFIRMATION-STATE-V1
repository: samindriano/idx-trade
branch: research/idx-price-trend-confirmation-state-v1
scope: deterministic outcome-blind HLCV price/trend/structure/confirmation state only

## Implemented

- `src/idx_trade/price_trend_state.py`
- `tests/test_price_trend_state.py`
- `docs/checkpoints/2026-08-15_PRICE_TREND_CONFIRMATION_STATE_V1_CONTRACT.md`

The layer uses raw H/L/C/Volume only, maps source session `t` to next official
feature session `t+1`, and emits separate categorical axes for trend, MA
structure, optional MA200 context, swing structure, volume, volatility, and
breakout confirmation.

No Foreign Flow merge, model fitting, score, expected return, trade
recommendation, outcome access, O2 change, free-float/HSC integration,
TradingView intraday dependency, scheduler, or forward counter is in scope.

## Local review sequence

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md`; claim/continue this
   exact lane before local execution and preserve every other lane.
2. Checkout `research/idx-price-trend-confirmation-state-v1`.
3. Run focused:
   `pytest -q tests/test_price_trend_state.py`
4. Run full `pytest` and `git diff --check`.
5. Adversarially inspect:
   - t -> t+1 causality;
   - target/future invariance;
   - rolling-window current-exclusion for breakout levels;
   - missingness / insufficient-history behavior;
   - duplicate/outcome-like input rejection;
   - no hidden dependency on Open or adjusted prices.
6. Do not tune any threshold from historical outcomes.
7. If tests expose an engineering bug, remediate only the contract
   implementation; do not change scientific thresholds unless the current
   definition is internally contradictory.
8. Commit/push any remediation, document exact test result, update TEAM_STATUS
   to REVIEW, and stop for independent review.

## Explicit next boundary

Do not yet wire this into Foreign Flow, canonical scheduler, ranking, or an
entry-eligibility decision.  After this state contract is independently
accepted, prospective sidecar wiring is a separate milestone.

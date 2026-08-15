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
- `tests/test_price_trend_state_prospective.py`
- `docs/checkpoints/2026-08-15_PRICE_TREND_CONFIRMATION_STATE_V1_CONTRACT.md`
- `docs/checkpoints/2026-08-15_PRICE_TREND_CONFIRMATION_STATE_V1_IMPLEMENTATION_CHECKPOINT.md`

The layer uses raw H/L/C/Volume only, maps source session `t` to next official
feature session `t+1`, and emits separate categorical axes for trend, MA
structure, optional MA200 context, swing structure, volume, volatility, and
breakout confirmation.

The prospective helper clips cached rows to `<=t` before full HLCV/duplicate
validation. Valid, invalid, or duplicate target/future rows therefore cannot
change the state built from source `t`. Malformed dates still fail closed, and
outcome-like columns remain globally forbidden.

No Foreign Flow merge, model fitting, score, expected return, trade
recommendation, outcome access, O2 change, free-float/HSC integration,
TradingView intraday dependency, scheduler, or forward counter is in scope.

## Validation already completed in GitHub Actions

Validation-only draft PR: `#26`.

- focused semantics + prospective isolation: **14 passed**;
- `git diff --check`: **PASS**;
- repository default CI: **53 passed, 1 failed, 4 warnings**;
- only failure is the known unrelated
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  mismatch (current storage reports `raw_close` and `vendor_adj_close` as two
  independent conflicts while the old test expects one).

Do not modify storage from this lane.

## Local review sequence

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md`; claim/continue this
   exact lane before local execution and preserve every other lane. This is
   still required because ChatGPT could not safely atomically append to the
   large shared canonical ledger through the available connector.
2. Checkout/pull `research/idx-price-trend-confirmation-state-v1`.
3. Confirm focused locally:
   `pytest -q tests/test_price_trend_state.py tests/test_price_trend_state_prospective.py`
4. Run full `pytest` and `git diff --check`.
5. Adversarially inspect:
   - t -> t+1 causality;
   - target/future invariance, including invalid future rows;
   - rolling-window current-exclusion for breakout levels;
   - missingness / insufficient-history behavior;
   - duplicate/outcome-like input rejection;
   - no hidden dependency on Open or adjusted prices.
6. Do not tune any threshold from historical outcomes.
7. If tests expose an engineering bug, remediate only the contract
   implementation; do not change frozen descriptive thresholds based on
   outcomes or historical performance.
8. Document exact local result, update canonical TEAM_STATUS to `REVIEW`, push,
   and stop for ChatGPT independent review.

## Explicit next boundary

Do not yet wire this into Foreign Flow, canonical scheduler, ranking, or an
entry-eligibility decision. After this state contract is independently
accepted, prospective sidecar wiring is a separate milestone and should reuse
the existing canonical EOD infrastructure with no new scheduler/counter.

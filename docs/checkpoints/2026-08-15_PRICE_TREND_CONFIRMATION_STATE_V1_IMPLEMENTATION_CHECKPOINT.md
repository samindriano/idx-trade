# Price / Trend / Confirmation State V1 — Implementation Checkpoint

Date: 2026-08-15 (Asia/Jakarta)

Branch: `research/idx-price-trend-confirmation-state-v1`

Marker: `PRICE_TREND_CONFIRMATION_STATE_V1_IMPLEMENTED_REVIEW_REQUIRED`

## Implemented scope

A deterministic outcome-blind state transformer now exists for raw daily
H/L/C/Volume.  Each completed source session `t` maps to the next official
feature session `t+1`.  The implementation is intentionally separate from
Foreign Flow, ranking models, O2, supply/free-float, and outcomes.

Outputs preserve raw evidence and separate categorical axes:

- `trend_state`
- `ma_structure_state`
- `long_term_state`
- `swing_structure_state`
- `volume_state`
- `volatility_state`
- `confirmation_state`

Main descriptive trend states:

- `DOWNTREND`
- `BASING`
- `EARLY_REVERSAL`
- `UPTREND`
- `TRANSITION`
- `INDETERMINATE`

Breakout confirmation is explicitly separated from trend and volume.  A
breakout with ordinary volume is not promoted to `BREAKOUT_CONFIRMED`.

## Guardrails

- H/L/C/Volume only; no Open dependency.
- Current session excluded from the prior-20 breakout level.
- Target/future rows are clipped out by the single-source prospective helper.
- Outcome-like columns are rejected.
- Invalid/nonfinite HLCV and duplicate identity are rejected.
- Insufficient rolling evidence returns `INDETERMINATE`.
- No score, probability, expected return, or trade recommendation.
- Thresholds are fixed engineering/descriptive defaults, not result-tuned.

## Validation state

A scoped GitHub Actions workflow is included only to execute the focused test
file in an isolated PR validation context.  No local/runtime/provider execution
has been performed by ChatGPT at this checkpoint.

Exact focused tests must pass before the implementation can be considered
reviewable.  Full repository pytest and `git diff --check` remain required in a
real checkout; the known unrelated storage revision-conflict expectation may
remain independently visible.

## Next boundary

Independent semantic/test review only.  Do not integrate with Foreign Flow or
produce ENTRY_ELIGIBLE/BUY semantics yet.

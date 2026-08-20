# Session-Aligned Counterfactual Sensitivity Audit V1 — Preregistration

Date: 2026-08-20 (Asia/Jakarta)
Parent: Feature-Window Session Semantics Audit V1

## Question

How much of the exact frozen V4-X final-fit representation would change if the row-based observed-bar windows were replaced, counterfactually and read-only, by strict official-IDX-session windows while holding the raw panel, primary-liquid universe, model definition, targets, and outcomes fixed?

## Counterfactual definition

The current representation is the frozen `build_v4_control_feature_table` output.

The counterfactual representation uses the same PIT-filtered panel and official IDX calendar, but computes stock-level source features on a full session grid with no forward fill, backward fill, synthetic prices, or search-back rescue:

- `close_return_5(t) = close(t) / close(t-5 official sessions) - 1`; unavailable if exact lag close is absent.
- `close_return_20(t)` analogously.
- ATR14 uses the immediately preceding official-session close and a 14-official-session rolling mean with the existing minimum-observation requirement.
- 20/60-session high-low windows are calendar bounded and use the existing `min_periods=window` requirement; missing session observations are not replaced by older observations.
- relative Volume20 and Regular-Market-Value20 use calendar-bounded 20-session medians with the existing minimum-observation requirement.
- the frozen V4 primary-liquid universe remains unchanged because its 60-session state is already explicitly exchange-session bounded.
- XS ranks, market context, and stock-minus-market features are recomputed only from the strict source features over the same frozen primary-liquid identities.

## Scope

Primary decision scope: exact frozen V4-X H5, H10, and H5∪H10 final-fit identities reconstructed from immutable final-fit training-date and support artifacts.

No historical performance, labels, targets, predictions, or protected-forward outcomes may be read.

## Required outputs

1. Source-feature direct change census, including finite-value changes and finite↔missing transitions.
2. Frozen 25-column V4 model-control representation change census.
3. Direct-vs-cross-sectional/market spillover attribution.
4. Per-feature change counts and affected ticker/date counts.
5. Gap attribution for rows with extended observed-bar windows:
   - pre-listing,
   - post-listing,
   - within-listed-domain missing panel session (`WITHIN_LISTING_NO_PANEL_ROW`),
   - unresolved if listing metadata is unavailable.
6. Compact row evidence for exact V4-X union support.

## Interpretation policy

This audit does not authorize a feature change. A material counterfactual delta would establish that observed-bar semantics are a meaningful architectural assumption and justify a separately frozen session-aligned challenger lineage. It must not be folded into the clean price-basis remediation/refit.

## Guardrails

- provider calls: false
- repair performed: false
- feature definition mutated in canonical code: false
- parent panel overwritten: false
- model fit: false
- model scoring: false
- target values accessed: false
- protected forward accessed: false
- primary-liquidity definition changed: false

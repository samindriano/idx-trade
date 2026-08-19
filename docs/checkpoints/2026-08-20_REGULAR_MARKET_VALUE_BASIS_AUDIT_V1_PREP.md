# Regular-Market Value Basis Audit V1 — Prepared

Date: 2026-08-20 Asia/Jakarta
Status: `AUDIT_PREPARED_RUNTIME_REQUIRED`
Branch: `audit/regular-market-value-basis-v1`

## Why this audit exists

The frozen V2/V4 research representation uses `regular_market_value` both as a rolling relative-value feature and as the absolute input to the 60-official-session primary-liquidity rule (`median_regular_value_60 >= Rp1,000,000,000`). H/L/C price-basis contamination is already confirmed on a separate remediation lane, but that remediation intentionally leaves Volume and Regular-Market Value unchanged.

## Official witness semantics

The existing IDX Stock Summary adapter preserves endpoint semantics explicitly:

- `Volume` and `Frequency` are Regular-Market order-book metrics;
- `NonRegularVolume` / `NonRegularFrequency` are retained separately;
- IDX Stock Summary `Value` is retained as `regular_value`.

Audit V1 therefore treats already-captured immutable Stock Summary `Value` as the official witness for `regular_market_value` on exact ticker/date overlap.

## Frozen scope

The audit is provider-free and outcome-blind. It compares the exact frozen panel SHA
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
and exact frozen calendar SHA
`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
against already-saved official Stock Summary raw JSON artifacts.

It reports:

1. official-witness date and ticker coverage denominator;
2. exact and tolerance-based panel-vs-IDX Value parity;
3. parity by `price_provenance` and year;
4. panel `regular_market_value / (close * volume)` versus official `Value / (Close * Volume)` diagnostics;
5. >=20% panel/IDX value-ratio seams and whether they coincide with price-provenance changes;
6. a bounded official-overlap counterfactual, without mutating the panel;
7. changes to `log_regular_value_relative_20`, its XS/market-relative representation, and `V4_PRIMARY_LIQUID_CAUSAL_V1` eligibility.

## Interpretation boundary

The official-overlap counterfactual is a lower-bound/bounded diagnostic. It does not authorize replacing value outside official overlap and is not a remediation. If material mismatch is confirmed, a separate preregistered Value remediation is required.

## Hard guardrails

- no provider calls;
- no model fit or scoring;
- no target/outcome materialization;
- no protected-forward access;
- no canonical/frozen parent overwrite;
- no implicit HLC/Volume/Value repair.

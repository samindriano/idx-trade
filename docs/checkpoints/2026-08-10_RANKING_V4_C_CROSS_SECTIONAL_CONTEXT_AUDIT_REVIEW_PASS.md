# Ranking V4-C Cross-Sectional Context Blind-Audit Review Pass

Date: 2026-08-10 (Asia/Jakarta)
Status: **INDEPENDENT BLIND-AUDIT REVIEW PASS / OUTCOME RUN MAY NOW BE SEPARATELY AUTHORIZED**

## Decision

`V4_C_CROSS_SECTIONAL_CONTEXT_BLIND_AUDIT_REVIEW_PASS`

The completed V4-C outcome-independent cache preparation and restricted feature audit are sufficient for the frozen first-pass design. No mechanical defect, coverage failure, causal-boundary violation, or preregistered redundancy-review trigger was reported.

This review does not change the frozen V4-C feature definitions, model, folds, target, or promotion gate.

## Reviewed repository state

- branch: `research/idx-ranking-v2-spec-v1`;
- reported audit HEAD/upstream: `498a465056c5f9f197e475e804a68297e2334adc`;
- working tree: clean and synchronized;
- full pytest: `357 passed`, `0 failed`, `3 warnings`, `16.31s`;
- V4-C spec Git blob: `43f222f31c7c0ea15e870d22b066aae95858c81f`.

## Frozen input identities

- signal-research panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- frozen V3-B late cache SHA-256: `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- frozen V3-B late manifest SHA-256: `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`.

## V4-C prepared cache

- status: `RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_CACHE_FROZEN_PRE_OUTCOME`;
- rows/tickers/dates: `286,453 / 737 / 1,205`;
- signal-session range: `20..1224`;
- primary-liquid cross-section count min/median/max: `222 / 267 / 433`;
- prepare runtime: `25.002s`;
- cache SHA-256: `480f09488c89128859921abe0617e51d04ac05d0ddfc42fb8f4d0c063f2b255e`;
- manifest SHA-256: `33ba2b39ce10476bea0566b2d240806a9d258ebe8c5f1b61733a539a397b7737`;
- `context_constructed_from_full_primary_universe=true`.

## Outcome-blind audit

- status: `RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_OUTCOME_BLIND_AUDIT_COMPLETE`;
- audit runtime: `17.262553s`;
- audit SHA-256: `913b0cf4462d762a6514d20d5ccaf4903210111def7f68aa3532f904c205ce78`.

Feature finite coverage:

| Feature | Row finite | Date finite |
|---|---:|---:|
| `v4c_market_return_iqr_5` | 100% | 100% |
| `v4c_market_return_iqr_20` | 99.9295% | 99.9170% |
| `v4c_market_atr_iqr` | 100% | 100% |
| `v4c_market_close_position_iqr_20` | 100% | 100% |

- constant features: none;
- finite-rate failures below `80%`: none;
- date-level absolute Spearman pairs at or above `0.95`: none;
- mechanical review required: `false`.

The highest reported date-level correlation involving V4-C was `0.759980` between `market_median_atr14_over_close` and `v4c_market_atr_iqr`. The highest row-level absolute correlation involving V4-C was `0.794918`. Neither approaches the frozen `0.95` mechanical-review threshold.

## Boundary verification

The audit explicitly reported or the returned run report confirmed:

- no V4-C candidate fitted or scored;
- no PR-AUC, ROC-AUC, Q5-Q1, paired, top-decile, or promotion result computed/inspected;
- context built from the full causal primary-liquid universe;
- session `1225+` not materialized;
- post-2026-07-31 fresh-forward outcomes untouched;
- ordinals `018..019` remain unviewed;
- cumulative historical evaluated-candidate count remains `12`;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten.

## Review interpretation

V4-C passes the frozen pre-outcome mechanical gate without any need or permission for redesign. Its four-feature bundle remains exactly as frozen. The audit result provides no basis to add alternate dispersion estimators, quantile bands, context thresholds, regime routing, or feature subsets.

V4-B has independently passed its own blind-audit review. Because V4-B and V4-C were both frozen and audited before either family opened outcomes, the remaining main V4 historical-development first passes may now be opened under a separate explicit joint authorization without adapting either design to the other's result.

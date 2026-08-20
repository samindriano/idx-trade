# Feature-Window Session Semantics Audit V1 — Runtime Result

Date: 2026-08-20 (Asia/Jakarta)
Branch: `audit/feature-window-session-semantics-v1`
Frozen implementation head before runtime: `39b5dd429020d361ab7ced2fd130abe4b1a61345`

## Decision

`OBSERVED_BAR_VS_EXCHANGE_SESSION_HORIZON_DIVERGENCE_CONFIRMED`

The audit confirms that the frozen V2/V4 control feature builder's per-ticker `shift`/`rolling` windows are observed-bar windows rather than strict official-IDX-session windows. This is a feature-semantics finding, not leakage and not evidence of additional raw-data corruption.

## Exact V4-X final-fit union

| Window | Extended rate among observable rows | Extended rows | Tickers | p99 effective sessions | Max effective sessions |
|---|---:|---:|---:|---:|---:|
| lag5 | 0.520842% | 1,259 | 163 | 5 | 40 |
| ATR14 | 1.367262% | 3,305 | 188 | 15 | 51 |
| lag20 | 2.151036% | 5,196 | 212 | 27 | 403 |
| rolling20 | 2.035793% | 4,921 | 204 | 27 | 57 |
| rolling60 | 6.590887% | 15,522 | 244 | 78 | 494 |

Exact V4-X union support: 241,724 rows / 629 tickers / 986 dates.

## Parent-integrity implication

The parent full-panel IDX integrity audit reported zero official ACTIVE valid-HLC rows missing from the frozen panel and complete 1,260-session calendar witness coverage. Therefore the observed-bar horizon extension cannot be attributed to ordinary missing official ACTIVE rows on the tested panel.

## Scientific boundary

Do not silently change V4-X feature definitions inside the price-basis remediation/refit. The deterministic clean V4-X replay must preserve the historical observed-bar feature semantics so the effect of the accepted HLC/Open data remediation remains isolated.

The next authorized step is an outcome-blind, no-fit counterfactual sensitivity audit comparing the current observed-bar representation to a strict official-session representation on exact V4-X fit support. If representation impact is material, any session-aligned feature design must be frozen as a separate challenger lineage (e.g. V4-X2) before inspecting clean-refit performance.

No model fit, model scoring, target-value access, protected-forward access, provider call, panel overwrite, or feature-definition mutation occurred in this audit.

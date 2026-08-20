# Frozen Panel Official IDX Integrity Audit V1 — Runtime Result

Date: 2026-08-20 (Asia/Jakarta)
Branch: `audit/frozen-panel-official-idx-integrity-v1`

## Decision

`FROZEN_PANEL_OFFICIAL_IDX_NO_MATERIAL_ISSUE_ON_TESTED_DIMENSIONS`

The full-panel audit completed successfully against the frozen 981,940-row signal-research panel and the saved official IDX Stock Summary corpus. This lane is audit-only and does not authorize repair, replay, model fit, model scoring, tuning, or protected-forward access.

## Runtime evidence

- Frozen panel rows: `981,940`
- Frozen panel tickers: `945`
- Official witness files: `1,288 / 1,288` accepted
- Official witness rows: `1,129,024`
- Official witness tickers: `983`
- Official witness period: `2021-04-01` through `2026-08-13`
- Output manifest SHA-256: `bf87e0c8ce49468113eec32cb7df931ff0df887444de727a57c65b495d87c016`

## Volume parity

- Exact overlap rows: `981,940 / 981,940`
- Exact rate: `1.0`
- Within 1% rate: `1.0`
- Mismatch rows: `0`
- Ratio seams >=20%: `0`
- Ratio seams coincident with price-provenance change: `0`
- Panel overlap rows without official ACTIVE valid HLC: `0`
- Official-volume counterfactual changed rows: `0` for direct volume, `relative_volume_20`, XS rank, market median, and market-relative representation.

## Coverage / missing-row integrity

No official ACTIVE + valid-HLC rows were missing from the frozen panel:

- Interior missing rows: `0`
- Leading missing rows: `0`
- Trailing missing rows: `0`
- Candidate missing rows total: `0`

## Calendar integrity

- Frozen calendar sessions: `1,260`
- Official ACTIVE witness dates inside window: `1,260`
- ACTIVE witness dates missing from calendar: `0`
- Calendar sessions without any Stock Summary witness: `0`
- Calendar sessions without any official ACTIVE + valid-HLC witness: `0`

## Remaining finding: provenance schema granularity

The panel has `price_provenance`, but lacks separate field-level provenance for:

- `open_provenance`
- `volume_provenance`
- `regular_market_value_provenance`

This is a lineage/governance weakness, not a measured data-value defect. The current runtime found no numeric mismatch in Volume or Regular-Market Value and no missing ACTIVE rows or calendar holes. Future consolidated-input lineage should preferably carry field-level provenance or an immutable sidecar mapping each field to its accepted source/derivation.

## Guardrails

- `repair_performed=false`
- `model_fit=false`
- `model_scoring=false`
- `target_values_accessed=false`
- `protected_forward_accessed=false`
- `provider_calls=false`
- parent panel unchanged

## Scientific disposition

On tested dimensions, the frozen panel is exonerated for full-panel Volume basis, official ACTIVE-row completeness, and calendar/session coverage. Together with the separate Regular-Market Value audit and price-basis HLC/Open remediation lanes, the remaining attack surface is now concentrated in other classes of risk: field-level provenance granularity, exact HLC parity/remediation consolidation, feature-window/session semantics, PIT universe/security-master semantics, and residual corporate-action/PIT coverage.

Status: **`DONE_NO_MATERIAL_ISSUE_ON_TESTED_DIMENSIONS`**.

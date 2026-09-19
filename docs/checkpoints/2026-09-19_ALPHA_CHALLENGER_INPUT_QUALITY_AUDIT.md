# Alpha Challenger Input Quality Audit

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-challenger-pit-safe-20260919`
Status: `READ-ONLY AUDIT — STRUCTURAL EVIDENCE ONLY`

## Boundary

This audit read existing local artifacts only. It did not call a provider,
write a runtime session, mutate a capture/cloud source, write a counter, open
protected targets, or modify incumbent/main data.

## Model-input snapshots

The runtime contained 28 `sessions/*/model_input.parquet` snapshots spanning
2026-08-03 through 2026-09-17. The observed schema was:

`ticker, date, high, low, close, volume, regular_market_value`

Across the snapshots:

- rows per session ranged from `827` to `837`;
- ticker count per session ranged from `827` to `837`;
- duplicate `(ticker, date)` keys: `0`;
- nulls in required columns: `0`;
- date-directory mismatches: `0`;
- non-finite numeric values: `0`;
- invalid H/L/C ordering or negative H/L/C: `0`;
- negative volume or market value: `0`.

This supports using the existing snapshots as structural input for a shadow
calculation. It does not certify historical corporate-action completeness or
execution-price semantics beyond the source artifacts' own attestations.

## V4-X1 score binding

The 15 clean V4-X1 prospective score artifacts from 2026-08-21 through
2026-09-17 contained `4,372` rows in total. Every artifact had unique
`(ticker, date)` keys, finite/non-null `alpha_consensus`, no target/label/
outcome/realized/forward-return columns, and `100%` key coverage against the
matching session `model_input.parquet` snapshot.

This is an identity/completeness check for the structural shadow input, not an
outcome evaluation.

## Price/Trend sidecar boundary

The accepted materialized Price/Trend State V1 artifact currently available is
for feature session `2026-08-13`, with `836` rows and no duplicate
`(ticker, feature_session)` keys. Its manifest reports:

- `state_contract_version = PRICE_TREND_CONFIRMATION_STATE_V1`;
- `outcome_blind = true`;
- `trade_recommendation = false`;
- `provider_calls = 0`;
- no null `ticker`, `source_session`, `feature_session`, or `trend_state`.

Some auxiliary warm-up/structure columns are sparse (for example, early
`ma_50`/`ma_200` fields and `recent_breakout_level_5`), but the fixed
challenger overlay consumes only the frozen `trend_state` plus identity fields.
This does not authorize treating the sparse auxiliary columns as alpha.

## Decision

Structural input checks: `PASS` for the audited shadow inputs.
PIT/OOS admission: `NOT PROVEN`; the canonical prospective evaluation remains
blocked at the project's current `2/100` production score sessions and the
materialized Price/Trend sidecar has only one date. No performance, superiority,
or promotion claim follows from this audit.

The next admissible evidence is a future, independently bound prospective
session or a separately authorized canonical evaluation. Capture, cloud, and
existing data sources remain untouched.

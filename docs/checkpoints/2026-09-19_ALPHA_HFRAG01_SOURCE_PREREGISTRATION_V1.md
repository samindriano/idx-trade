# H-FRAG-01 Official Stock-Summary Composition — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PARTIAL_SOURCE_DIAGNOSTIC / NOT_ADMITTED / NO_C5`

## Question

Does the official IDX stock-summary cache contain a stable, distinct
regular-versus-non-regular trading-composition surface that is worth preserving
as a future target-free research direction, or is it only a duplicate of the
existing volume/value inputs?

This is a source-capability and structural-signature audit. It is not a
predictive test and cannot produce IC, ICIR, OOS, P&L, candidate superiority,
or a C5 admission.

## Source and grain

- Source directory:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\stock_summary_cache_1260\`.
- Expected grain: one official `ticker` × `as_of_date` row per parquet date
  file, with one matching `.meta.json` sidecar.
- Fields under test: `frequency`, `nonregular_volume`, and
  `nonregular_frequency`.
- Duplicate controls: `volume` and `regular_value` are treated only as
  reconciliation fields because they are expected to duplicate the frozen
  panel's `volume` and `regular_market_value`.
- Source semantics remain unadmitted until the meaning, publication timing,
  revision behavior, and regular/non-regular classification are independently
  documented.

## Frozen checks

1. Inventory all 1,260 parquet and 1,260 sidecar files; compute a deterministic
   filename/content inventory hash.
2. Validate row grain, duplicate keys, official-session membership, date range,
   source identity, sidecar row counts, nulls, finite values, and negative
   values.
3. Reconcile cache `volume` and `regular_value` to the frozen panel on exact
   `(ticker,date)` overlap; report cache-only and panel-only rows separately.
4. On the existing eligible decision universe only, compute source-capability
   summaries for:
   - `nonregular_volume / volume` when both are positive/finite;
   - `nonregular_frequency / frequency` when both are positive/finite;
   - coverage, quantiles, boundedness violations, ticker/date breadth, and
     bottom-value Q1 concentration of high-share rows.
5. Report structural rank/Top-30 overlap only on the latest 600 common official
   sessions against C1/C2/C4 and H-LIQ; no score is registered as a candidate
   and no target is read. Source-capability inventory still covers all 1,260
   sessions.

## Fail-closed interpretation rules

- `ADMISSIBLE` is not allowed from this audit alone. The surface is at most
  `PARTIAL` until row-level available-at/knowledge-time, revision/vintage,
  issuer/security identity, and exact field semantics are established.
- A field ratio outside `[0,1]`, source/date/key inconsistency, or sidecar
  mismatch is a validity failure, not a clipping opportunity.
- `volume` and `regular_value` agreement is reconciliation evidence only; it
  does not make the non-regular fields PIT-admissible.
- No parameter sweep, target proxy, sign choice, clipping, winsorization,
  candidate ID, status upgrade, or packet expansion is permitted.

## Decision outcomes

- `SOURCE_PARTIAL_STRUCTURAL_SIGNAL`: fields are valid enough to preserve as a
  bounded future hypothesis but remain source-admission blocked.
- `SOURCE_BLOCKED`: grain, source, timing, or validity fails materially.
- `SOURCE_REDUNDANT`: no distinct non-regular composition remains after exact
  reconciliation and structural diagnostics.

The result must preserve exact source hashes, inventory hash, code hash, access
flags, and the reason the surface remains outside the protected packet.

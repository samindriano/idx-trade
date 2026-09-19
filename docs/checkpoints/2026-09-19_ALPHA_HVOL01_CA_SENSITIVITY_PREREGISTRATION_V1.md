# H-VOL-01 Corporate-Action Sensitivity — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `B_J_CORPORATE_ACTION_PRICE_BASIS_EXPOSURE_AUDIT`

## Question

Does the fixed H-VOL-01 daily volatility-compression representation change
materially when the retained `idx_close` comparison values are substituted for
the 188 unresolved non-stable-scale rows already used in the CA forensic lane?

This reduces a new uncertainty: the H-VOL-01 structural result is not useful
for re-entry planning if its low overlap or turnover profile depends on an
unresolved price basis.

## Fixed method

- Baseline: the guarded clean OHLCV panel and the frozen official-session/
  tradability-universe construction.
- Counterfactual: replace `close` in memory only for keys present in
  `unresolved_nonstable_scale_basis_rows.csv`, using its retained `idx_close`
  comparison value. These values are not treated as an admitted correction.
- Score: exactly the preregistered H-VOL-01 formula
  `-log(median_5((high-low)/close) / median_60((high-low)/close))`.
- Comparison: finite score changes, daily rank changes, Top-30 set overlap,
  changed Top-30 dates, and direct-versus-spillover classification by whether
  the changed row key is inside the 188-row artifact.
- No target, forward return, incumbent score, parameter sweep, sign flip,
  threshold search, refit, candidate creation, or panel write is permitted.

## Decision rule

The result is descriptive forensic evidence only. It may strengthen a
price-basis caution or show bounded stability, but it cannot clear PIT/CA
admission, authorize a clean refit, or promote H-VOL-01 to C5.

## Inputs and boundary

Use only the already retained local panel, guarded official sessions and
anchors, guarded feature eligibility, manifest, and the unresolved-scale
comparison artifact. Write only the derived JSON to the isolated external
staging root. Stop on hash, key, eligibility, schema, or provenance mismatch.

## Expected information gain

If H-VOL is sensitive, its structural distinctness is not yet reliable and
the mechanism stays blocked on basis evidence. If it is stable, the result
narrowly separates H-VOL's remaining novelty/economic questions from this
specific 188-row basis risk while leaving global CA completeness unresolved.

# Price-Basis Volume/Value Audit V1 — Preparation

Date: 2026-08-20 Asia/Jakarta  
Branch: `data/price-basis-remediation-v1`

## Trigger

H/L/C remediation V1 materialized successfully with runtime manifest SHA-256
`2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278`.
The repaired panel remains intentionally unchanged for `volume` and
`regular_market_value`. Clean V2/V4-X refit is still unauthorized until those
fields are checked for corporate-action or unit-scale basis contamination.

## Frozen population

The audit is restricted to the exact 1,657 H/L/C remediation identities across
12 tickers. The population may not expand after results are seen.

Official comparator is the already-stored IDX Stock Summary archive. Runtime is
offline; no provider/network call is authorized. Exact official field names are
frozen as `Volume` and `Value`; the runner does not silently substitute aliases.

## Diagnostics

For each frozen row and each field:

- compute `panel / official_IDX` ratio;
- classify as `SAME_BASIS`, `CA_FACTOR`, `INVERSE_CA_FACTOR`, `OTHER_RATIO`, or
  `INVALID_OR_MISSING` using `rtol=atol=1e-6` against the independently frozen
  CA factor;
- require repeated CA-factor evidence on at least 3 rows of a ticker before
  declaring field-level CA-factor basis remediation required;
- independently detect any repeated non-1 ratio, rounded to 8 decimals, present
  on at least 3 rows of the same ticker. This catches persistent unit/scale
  mismatches even if they are unrelated to the CA factor.

General one-off vendor differences are retained as diagnostics and are not
silently repaired by this audit.

## Adjudication

- incomplete official support on either field ->
  `VOLUME_VALUE_BASIS_AUDIT_INCOMPLETE_OFFICIAL_SUPPORT`;
- repeated CA-factor or repeated non-unit scale evidence on either field ->
  `VOLUME_VALUE_BASIS_SCALE_EVIDENCE_FOUND_REMEDIATION_REVIEW_REQUIRED`;
- otherwise ->
  `NO_REPEATED_VOLUME_VALUE_BASIS_SCALE_EVIDENCE_REFIT_REVIEW_READY`.

The third verdict only makes the lineage eligible for independent clean-refit
review; it does not itself fit a model.

## Prohibited actions

- volume/value repair during this audit;
- model fit or scoring;
- target-value access;
- protected-forward access;
- provider/network calls;
- parent/remediated panel overwrite;
- TradingView full acquisition or Path Risk restart.

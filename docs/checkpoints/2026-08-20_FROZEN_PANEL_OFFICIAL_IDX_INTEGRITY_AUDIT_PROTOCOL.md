# Frozen Panel Official IDX Integrity Audit V1

Date: 2026-08-20 Asia/Jakarta  
Status: `AUDIT_PROTOCOL_FROZEN_RUNTIME_PENDING`  
Branch: `audit/frozen-panel-official-idx-integrity-v1`

## Purpose

Adversarially test data dimensions not closed by Price-Basis HLC Remediation V1. The remediation branch already owns a bounded Volume/Value check on the 1,657 HLC-repaired rows and Open/HLC recertification. This audit instead attacks the **entire frozen 981,940-row signal-research panel** using already-captured official IDX Stock Summary evidence.

## Frozen inputs

- signal panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- official calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- official witness: immutable local `stock_summary.raw.json` corpus already captured under the historical Foreign Flow artifact root.

No new provider acquisition is permitted.

## Tests

1. **Full-panel Volume parity**
   - exact ticker/date overlap;
   - `panel.volume` vs official IDX regular-market `Volume`;
   - exact and ±1% rates;
   - ratio distributions;
   - ratio seams >=20%, including coincidence with `price_provenance` changes.

2. **Official activity semantics**
   - every panel overlap is checked against official positive `Volume`, positive `Frequency`, and valid positive H/L/C envelope.

3. **Calendar witness integrity**
   - official ACTIVE + valid-HLC dates inside the frozen calendar bounds but absent from the frozen calendar;
   - frozen sessions without any Stock Summary witness;
   - frozen sessions without any official ACTIVE + valid-HLC row.

4. **Official ACTIVE/HLC-valid rows missing from the panel**
   - scope is limited to tickers appearing somewhere in the frozen panel and dates in the frozen calendar;
   - missing rows are classified as leading, trailing, or **interior** relative to each ticker's observed panel range;
   - interior gaps are highest-priority forensic candidates;
   - candidates are not automatically declared bugs because listing, warm-up, CA integrity, or other admission-domain rules may explain them.

5. **Bounded official-Volume counterfactual**
   - official Volume replaces panel Volume in memory on exact overlap only;
   - primary-liquid membership is held fixed because its frozen definition is driven by `regular_market_value`, already independently exonerated;
   - recompute only the Volume representation relevant to V2/V4: `relative_volume_20`, same-date XS rank, market median, and stock-minus-market value;
   - quantify direct and cross-sectional spillover without model fitting/scoring.

6. **Field-level provenance schema**
   - record whether separate provenance exists for Volume, Regular-Market Value, and Open rather than relying only on row-level `price_provenance`.
   - provenance under-specification is a governance weakness, not evidence that numeric data are wrong.

## Guardrails

- outcome-blind;
- zero provider/network calls;
- no model fit/scoring;
- no target/return/rank/performance materialization;
- no protected-forward access;
- no canonical panel overwrite;
- no repair or refit authorization.

## Runtime boundary

Run focused tests first, then exactly one local audit against the frozen local bytes. Stop for independent review regardless of verdict.

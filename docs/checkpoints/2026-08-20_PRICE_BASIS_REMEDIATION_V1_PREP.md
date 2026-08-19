# Price-Basis Remediation V1 — Preparation

Date: 2026-08-20 Asia/Jakarta  
Branch: `data/price-basis-remediation-v1`

## Trigger

Step-2 audit V1.2 confirmed price-basis contamination in frozen V2 and V4-X1
training representations. Parent evidence is immutable:

- V1.1 manifest SHA-256 `62562fa3f1d949c3e4f9e225aae13b116a5e2c00dffcceab6240ebb07ea422d6`;
- V1.2 manifest SHA-256 `620fbd1f98924365e623919d3339f005abd7960f66631213631b845dcd7061f5`;
- frozen panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- 1,657 stable multiplicative H/L/C basis rows across 12 tickers, all parent provenance `YAHOO_RAW`;
- V2 prepared representation: 52,554 changed rows under the frozen HLC counterfactual;
- V4-X1 exact H5/H10 union: 56,602 changed rows under the same counterfactual.

## Independent corporate-action corroboration

The 12 observed stable factors are independently corroborated by KSEI security
corporate-action records. The frozen certification table is
`config/price_basis_remediation_v1.csv`. It includes both mandatory conversions
(stock-split-like share-count changes) and rights distributions. This matters:
not every observed multiplicative Yahoo historical adjustment is a stock split.

Certification is corroboration, not the price oracle. Official IDX Stock Summary
remains the raw H/L/C oracle. A row is remediated only when all frozen conditions
hold:

1. parent Step-2 classification is `stable_scale_run_member=true`;
2. parent `price_provenance=YAHOO_RAW`;
3. observed multiplicative factor matches the independently certified KSEI
   share-count factor within `rtol=atol=1e-6`;
4. session date is strictly before the certified corporate-action record date;
5. official IDX H/L/C are present from the parent audit evidence.

All 1,657 parent stable rows / 12 tickers must pass. Any failure stops the run;
there is no partial best-effort repair.

## Mutation boundary

V1 is H/L/C-only. It materializes a new immutable panel and a field-level HLC
overlay. The original panel is never overwritten. `volume`,
`regular_market_value`, row identity, row-level `price_provenance`, and every
other column must remain byte/value-equivalent at dataframe semantics.

The row-level parent `price_provenance` is intentionally retained rather than
falsely relabeling the entire row as IDX: only H/L/C are overridden. The overlay
carries `hlc_override_provenance=IDX_PUBLIC_STOCK_SUMMARY` and the parent
provenance explicitly.

The new overlay must be exactly identical in ticker/date and remediated H/L/C to
the V1.1 counterfactual that produced the accepted training-impact audit. This
prevents the remediation implementation from changing the scientific treatment
after observing model-lineage impact.

## Explicit non-scope

- no model fit/refit;
- no scoring or rank comparison;
- no historical target-value access;
- no protected prospective outcome access;
- no provider/network calls at runtime;
- no overwrite of V2/V4-X1 or the parent research panel;
- no repair of non-stable or otherwise unresolved mismatches;
- no volume/value repair in V1;
- no TradingView full acquisition or Path Risk restart.

## Stop condition

After local materialization, stop for review. A bounded volume/value-basis audit
is required before any clean model refit is authorized. This is specifically to
avoid declaring the training panel fully clean after correcting H/L/C while a
possible Yahoo corporate-action volume/value basis issue remains untested.

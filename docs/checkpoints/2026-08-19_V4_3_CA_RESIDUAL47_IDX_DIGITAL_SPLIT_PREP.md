# V4-3 CA residual-47 IDX Digital Statistic split prep

Status: `PREPARED_OUTCOME_BLIND_FINAL_CA_SOURCE_ATTEMPT`

## Parent

- combined replay manifest: `12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`
- parent verdict: `V4_3_CA_IDX_COMBINED_REPLAY_BLOCKED_REVIEW_REQUIRED`
- original schedule events resolved: 33/80
- residual schedule events: 47
- worst frozen H5: 0.8432203389830508
- worst frozen H10 / consensus: 0.8395061728395061
- fold-head training sets remain incomplete.

## Final bounded source attempt

Use only official IDX Digital Statistic `LINK_STOCK_SPLIT` monthly records. Query scope is derived from every residual event's frozen source dates with a symmetric +/-2 month window. No pass-impact ranking or subset selection is permitted.

Only stock-split / reverse-split family events are semantically eligible. An exact transition may be admitted only when:

1. ticker identity is exact;
2. source family and structured action type are compatible;
3. IDX `ListingDate` is within the preregistered linkage window around frozen source dates;
4. that `ListingDate` is an official IDX session;
5. all admissible candidate rows agree on one distinct listing date; and
6. raw response provenance is SHA-pinned.

`ListingDate` is mapped only to `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE` for this structured stock-split dataset. Source/record/distribution dates are linkage only and are never promoted to transition dates. Non-split families remain unresolved.

## Stop rule

This is the final structured CA acquisition attempt for this generation. If semantic yield is zero or too small to materially change the continuity gate, park V4-3 as blocked by the preregistered CA gate rather than opening another broad provider/issuer crawl. No target/model/performance/protected outcome access occurred during preparation.

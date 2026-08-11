# TradingView Identity/Provider Remediation — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/idx-open-backfill-tradingview-identity-remediation-v1`
Reviewed runtime HEAD: `2d2940448163532b1aaf6b5eca8ff756ebab403b`
Decision: `SMBR_SINGLE_OPEN_CANDIDATE_ACCEPTED_IDENTITY_LANE_CLOSED_FOR_CURRENT_CONTRACT`

## Review conclusion

The frozen 2,877-row identity/provider remediation runtime is accepted.

The single SMBR row on 2023-03-14 is admissible under the unchanged TradingView gate:

- exact ticker/date;
- certified H/L/C exact at 388 / 372 / 372;
- positive Open = 388;
- Open lies inside certified Low-High;
- canonical ticker contract succeeded with HTTP 200 and 1,000 candles;
- no alternate-symbol guess was used.

The remaining 2,876 rows are treated as unresolved under the current TradingView contract. No evidenced alternate ticker alias exists in the preserved project identity evidence for FREN, MASA, MFIN, RMBA, or TURI; therefore no speculative alias retry is authorized.

## Updated Open accounting if the one accepted row is applied to a new derivative

- current Yahoo + TradingView derivative rows: 981,940;
- current null Open: 43,801;
- newly accepted SMBR Open rows: 1;
- resulting null Open: 43,800;
- resulting known Open rows: 938,140;
- resulting global Open coverage: 95.5394423%;
- immutable certified panel remains unchanged.

This one-row improvement is too small to justify further identity-provider work before measuring research-universe coverage.

## Next decision

Do not continue chasing provider identity in the same lane.

The next authorized research task is an Open research-grade coverage gate against the exact frozen V3-B Structure-Lite research universe. The purpose is to decide whether remaining global Open gaps materially affect the rows actually used by the alpha research pipeline.

The coverage gate must:

1. start from the accepted Yahoo + TradingView derivative and apply only the one accepted SMBR row to a new derivative or equivalent read-only overlay;
2. reproduce the exact V3-B eligibility/universe logic from repository artifacts/code rather than approximating it from global rows;
3. report Open availability on all V3-B model-eligible rows and, where reproducible from frozen artifacts, the exact historical development/refit population;
4. report coverage by year, ticker, session, and any frozen train/validation/test or walk-forward partitions used by the historical V3-B research;
5. quantify how many rows would be lost by requiring Open and how concentrated those losses are;
6. evaluate causal Open-derived feature availability after necessary one-day lag/lookback/warm-up semantics, without fitting any new model;
7. compare HLCV baseline and future OHLCV challenger on the same Open-eligible row set as a required future fairness rule;
8. produce a factual PASS / CONDITIONAL_PASS / FAIL recommendation for OHLCV alpha research only.

This task must not train or tune an OHLCV model, peek at protected fresh-forward outcomes, repair corporate actions, modify the immutable panel, or promote execution grade.

Execution-grade completeness and research-grade OHLCV eligibility are separate decisions.

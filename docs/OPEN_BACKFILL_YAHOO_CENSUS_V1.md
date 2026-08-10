# Historical Open Backfill — Yahoo Full-Universe Recovery Census V1

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-yahoo-census-v1`
Parent decision: `YAHOO_SEMANTICS_AUDIT_ACCEPTED_FULL_UNIVERSE_RECOVERY_CENSUS_AUTHORIZED`.

## Purpose

Measure actual full-universe recoverability of historical `Open` for the immutable 1260-session IDX research panel using Yahoo raw daily OHLC as candidate evidence under the already frozen fail-closed contract.

This stage may create a derivative candidate panel outside Git. It must not overwrite the immutable panel and must not promote execution-grade status automatically.

## Immutable baseline

- window: `2021-04-29 -> 2026-07-31`;
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- ACTIVE rows: `981,940`;
- unresolved Open baseline: `446,843`;
- existing non-null Open is immutable;
- `execution_grade_promoted=false`.

## Yahoo semantics

Use Yahoo/yfinance raw OHLC with `auto_adjust=False`. `Adj Close`, dividends, and action metadata may be retained for diagnostics only and never substituted into execution prices.

The full-universe run must be resumable. Raw provider results must be cached outside Git and keyed by ticker, requested date range, provider semantics, and retrieval metadata. Network retries must not alter admission rules.

## Direct admission contract

A missing Open row is directly admissible only when:

1. ticker/security identity matches exactly;
2. session date matches exactly;
3. raw Yahoo High equals certified panel High;
4. raw Yahoo Low equals certified panel Low;
5. raw Yahoo Close equals certified panel Close;
6. raw Yahoo Open is finite and `> 0`;
7. raw Yahoo Open lies inside certified `[Low, High]`.

Existing non-null Open is never overwritten.

## Verified split-scale path

A candidate that fails direct H/L/C equality may be considered only under a separately classified split/reverse-split reconstruction path:

- factor comes from independently verified pre-existing official split/reverse-split evidence;
- factor is not fitted or inferred from Yahoo/panel ratios;
- one cumulative factor transforms Open/High/Low/Close consistently;
- transformed H/L/C must equal certified H/L/C exactly;
- transformed Open must be finite, positive, and within certified `[Low, High]`;
- accepted rows are tagged `SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE` and remain distinguishable from direct evidence.

No dividend adjustment, Adj Close, interpolation, previous Close substitution, source averaging, or synthetic Open is allowed.

## Fetch strategy

Prefer a robust resumable implementation over maximum throughput.

- exact panel ticker list only;
- full requested window per ticker;
- bounded concurrency / retry with backoff;
- raw cache outside Git;
- cached completed tickers are not fetched again unless an explicit cache-integrity check fails;
- provider errors remain explicit and do not become `NO_TRADE` or synthetic evidence;
- preserve retrieval timestamps, yfinance/provider version where available, request ranges, and raw/cache hashes.

## Required full known-answer audit

All existing non-null Open rows with a Yahoo candidate must be evaluated, not sampled.

Report separately:

- exact ticker/date coverage;
- direct H/L/C exact rate;
- direct Open exact rate;
- split-scale reconstructable known rows;
- reconstructed Open exact rate;
- mismatches by year, ticker, and diagnostic.

This audit is a source-quality gate. Do not hide mismatching known-answer rows merely because missing rows can be filled.

## Derivative candidate output

The runner may create a derivative candidate panel outside Git. It must:

- start from the immutable certified signal panel;
- preserve every existing non-null Open unchanged;
- fill only rows that pass direct or verified split-scale admission;
- include provenance fields sufficient to identify source, evidence class, retrieval/cache reference, validation status, and split factor where applicable;
- retain unresolved rows as null;
- hash the derivative and manifest.

The derivative is a candidate execution-data artifact only. It is not automatically certified execution-grade.

## Required reporting

At minimum:

- exact code/branch/HEAD;
- pytest result;
- immutable panel SHA before/after;
- ticker count attempted / returned / unsupported;
- provider request, retry, and error counts;
- raw-cache file count and manifest hash;
- all-provider-row count;
- exact ticker/date coverage;
- full known-answer H/L/C and Open agreement;
- direct accepted missing-Open count;
- verified split-scale accepted missing-Open count;
- total accepted fill count;
- initial and final missing Open count;
- actual gap-closure percentage;
- accepted/rejected counts by year;
- rejection histogram;
- unsupported/error ticker list or summary;
- temporal coverage/degradation summary;
- derivative artifact SHA-256;
- provenance/manifest SHA-256;
- confirmation `execution_grade_promoted=false`.

## Stop boundary

After the full-universe census completes, STOP for independent ChatGPT review. Do not start execution-PnL, paper/live trading, broker integration, or execution-grade promotion. Do not modify Ranking V1/V2 or rerun Stage 5.

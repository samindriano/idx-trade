# V2 migration audit map

This file tracks the disposition of findings from the `market-movement-analyzer` audit so V2 does not silently reintroduce them.

## Critical findings

| V1 finding | V2 disposition | Status |
|---|---|---|
| Missing bar, suspension and provider gap were conflated | Separate existence, market-specific tradability and provider availability states | IMPLEMENTED FOUNDATION |
| Suspended/no-trade outcomes could be dropped from labels | New outcome engine must retain execution-state outcomes; no V1 label code will be migrated | PENDING MODEL PHASE |
| Security master tracked listing but not tradability | Separate `security_master` and market-specific `tradability_intervals` | IMPLEMENTED FOUNDATION |
| Coverage passed when a ticker merely had >=60 rows | Expected-vs-observed exchange-session coverage with internal-gap audit | IMPLEMENTED FOUNDATION |
| Pilot/current-active universe could create survivorship bias | Historical universe built as-of date from listing/tradability state and trailing liquidity | IMPLEMENTED FOUNDATION |
| V1 portfolio backtest compounded overlapping 5-day trades incorrectly | V1 backtest will not be migrated; V2 requires event-driven cash/exposure accounting | PENDING SIMULATOR PHASE |

## High findings

| V1 finding | V2 disposition | Status |
|---|---|---|
| Adjusted OHLC overwrote executable raw prices | Preserve `raw_*`; vendor adjusted close stored separately | IMPLEMENTED FOUNDATION |
| Yahoo adjusted-close factor can include distributions, not only splits | Do not synthesize split-adjusted technical OHLC from Adj Close | IMPLEMENTED FOUNDATION |
| Corporate-action sequential calculation happened before canonical sorting | Sort/dedupe before any `pct_change`/rolling operation | IMPLEMENTED FOUNDATION |
| Imported delisted archives could lack corporate-action provenance | Archive ingestion must require provenance and explicit action-quality status | PENDING INGESTION PHASE |
| Cross-sectional features depended on whichever names were present in the dataset | Cross-sectional features may only use a point-in-time eligible universe | PENDING FEATURE PHASE |
| Forward monitor required every currently-listed ticker to have a bar, so valid suspensions could block the full snapshot | Monitoring must evaluate expected Regular-Market tradability before requiring a bar | PENDING MONITOR PHASE |
| Non-mature suspend/delist outcomes could be excluded from performance metrics | New evaluation must report unresolved/execution-risk outcomes explicitly and cannot mark review complete by dropping them | PENDING MONITOR PHASE |
| `confidence` represented different probability objects in different code paths | V2 schema separates opportunity score, calibrated probability and estimate reliability | PENDING MODEL PHASE |
| Reused holdout was labeled but not technically protected | Experiment registry must freeze a holdout/use history and reject reuse as an untouched test | PENDING EVALUATION PHASE |

## Reproducibility findings

| V1 finding | V2 disposition | Status |
|---|---|---|
| Model/config source was hashed but package environment was not | `provenance.environment_manifest` records exact installed versions + source/data hashes | IMPLEMENTED FOUNDATION |
| `monitor.py` evaluation logic was outside the frozen protocol hash | V2 run protocol must hash prediction and evaluation code paths | PENDING MONITOR PHASE |
| Requirements used version ranges | Keep development constraints, but each run must persist exact installed versions/lock fingerprint | IMPLEMENTED FOUNDATION |

## IDX-specific schema correction discovered during V2 migration

IDX announcements can suspend/unsuspend different markets differently (for example a negotiated-market-only opening). V2 therefore stores `market` on every tradability interval and resolves Regular Market independently. An `ALL` interval is only a fallback; an exact-market interval overrides it.

## Explicitly not migrated from V1

- anomaly score weights;
- `BULLISH/BEARISH/NEUTRAL` fixed five-session objective;
- old `confidence` column semantics;
- old financial backtest;
- old current-active pilot selection;
- old row-count coverage gate.

## Components eligible for selective porting

- IDX listing/delisting reference retrieval;
- Yahoo raw daily downloader/retry ideas;
- atomic persistence ideas;
- chronological splitting and purge/embargo concepts;
- calibration infrastructure concepts;
- immutable run/ledger concepts, after monitor protocol is redesigned.

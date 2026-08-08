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

## Data-foundation additions after audit

| Requirement | V2 implementation | Status |
|---|---|---|
| Official suspension/resumption events need auditable provenance | Manifest-driven IDX PDF ingestion records source URL, document hash, parser version and diagnostics | IMPLEMENTED FOUNDATION |
| Stock and warrant market scopes can coexist in one announcement | Equity parser prefers explicit stock Regular/Cash/Negotiated scope over unrelated warrant `Seluruh Pasar` text | IMPLEMENTED FOUNDATION |
| Intraday negotiated-only opening/resuspension cannot be represented as a normal daily state | Complex intraday documents are `MANUAL_REVIEW`; no automatic interval is emitted | IMPLEMENTED FOUNDATION |
| Periodic Call Auction/later-session resumptions are only partially tradable days | Call-auction or later-session resume documents are `MANUAL_REVIEW` for the daily engine | IMPLEMENTED FOUNDATION |
| Successful parsing must not imply historical source completeness | Ingestion integrity report always keeps `coverage_complete=false`; coverage windows require a separate discovery audit | IMPLEMENTED FOUNDATION |
| Data pipeline needs hostile real-world QA cases before ML | Versioned adversarial catalog covers normal liquid, IPO, suspend/resume, long suspension, delisted, complex market scope and data-quality stress cases | IMPLEMENTED FOUNDATION |
| Missing price-semantics verification must fail closed | Absent `price_semantics_verified` flag is a hard DATA GATE blocker | IMPLEMENTED FOUNDATION |
| Historical suspension discovery completeness is still unknown | Backfill/discovery audit must justify the usable Regular-Market research period; otherwise shorten the period | PENDING DATA BACKFILL |
| Corporate-action provenance over delisted/imported history is still incomplete | Verify explicit split/dividend/action history before technical-price layer or model development | PENDING DATA BACKFILL |

## Reproducibility findings

| V1 finding | V2 disposition | Status |
|---|---|---|
| Model/config source was hashed but package environment was not | `provenance.environment_manifest` records exact installed versions + source/data hashes | IMPLEMENTED FOUNDATION |
| `monitor.py` evaluation logic was outside the frozen protocol hash | V2 run protocol must hash prediction and evaluation code paths | PENDING MONITOR PHASE |
| Requirements used version ranges | Keep development constraints, but each run must persist exact installed versions/lock fingerprint | IMPLEMENTED FOUNDATION |

## IDX-specific schema corrections discovered during V2 migration

IDX announcements can suspend/unsuspend different markets differently. V2 therefore stores `market` on every tradability interval and resolves Regular Market independently. An `ALL` interval is only a fallback; an exact-market interval overrides it.

Some IDX resumptions are intraday or happen only in later Periodic Call Auction sessions. Those dates are not flattened into a normal full-day `ACTIVE` state in the daily model; the parser rejects them to manual review until the daily-state treatment is explicitly resolved.

## Data-gate policy

- `PASS`: freeze a versioned data snapshot and begin support/resistance/setup research.
- `FAIL`: fix data, obtain better evidence, or shorten the research period.
- `UNKNOWN`: remains a failure for model development.
- Never weaken the gate merely to preserve an ambitious 2009-present history.

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

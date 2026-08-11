# Stockbit Intraday Broad Current-Universe Census — Frozen Spec

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/stockbit-intraday-forward-capture-v1`
Status: `AUTHORIZED_AFTER_TESTS_PASS`

## Decision

`STOCKBIT_INTRADAY_20260811_CURRENT_UNIVERSE_BROAD_CENSUS_AUTHORIZED`

The 12-ticker post-close pilot passed cleanly. Before authorizing a recurring 300–1000 ticker daily farm, run one broad census for the still-current 2026-08-11 Stockbit `timeframe=today` session.

This is time-sensitive evidence acquisition: the provider contract is today-only, so the 2026-08-11 session may no longer be recoverable once the provider rolls to the next date.

## Prerequisite

The newly added resumable farm implementation and its focused tests must pass before any broad network run. Implementation-only defects may be fixed without widening this frozen scope. Run full pytest after focused tests.

## Universe

Use the repository's existing official IDX current active-stock reference provider (`fetch_active_listings`) at runtime.

Freeze the exact returned universe before Stockbit calls:

- source label: `IDX_CURRENT_ACTIVE_STOCK_LIST`
- expected date: `2026-08-11`
- exact CSV snapshot
- exact ticker count
- deterministic ticker-list SHA-256
- universe snapshot SHA-256

Do not use the historical 979-ticker panel as the capture universe. Do not silently delete illiquid names because they return fewer points. Do not include non-stock instruments outside the IDX stock-list response.

If the frozen current universe exceeds 1,200 tickers or is empty, STOP for review.

## Capture contract

Use the resumable daily farm only.

- endpoint: existing Zapi `finance:stockbit/chart`
- one request per current active IDX stock ticker
- `symbol=<ticker>`
- omit `count`
- require provider=`stockbit`
- require interval=`intraday`
- require timeframe=`today`
- require exact expected session date `2026-08-11`
- no `--allow-partial-session`
- run only after the existing 16:15 Asia/Jakarta close gate
- max new tickers: 1,200
- monthly quota reserve: 3,000

The collector must remain resumable and must never refetch a ticker already persisted with terminal `SUCCESS` within the same frozen day root.

If the provider has rolled away from 2026-08-11 (for example responses validate as another session date), STOP. Do not change `expected_date` to rescue the run.

## Data semantics

This Stockbit endpoint is an intraday price-path archive, not minute OHLCV.

Preserve exactly what the provider returns and normalized evidence fields already admitted by the pilot. Do not invent:

- minute OHLC
- minute volume
- bid/offer
- missing clock minutes
- interpolated prices
- forward-filled prices

A ticker with sparse provider timestamps is still valid evidence; sparsity must be measured, not repaired.

## Artifact policy

Use a new immutable dated external root for the full 2026-08-11 census. The resumable layout must preserve at least:

- frozen universe snapshot + metadata
- per-ticker raw payload
- per-ticker normalized rows
- per-ticker status
- consolidated final rows/status
- run summary
- recursive artifact manifest

No API key may be printed or persisted.

## Required report

Report:

- frozen universe ticker count and hashes
- attempted / successful / unfinished ticker counts
- exact status-class breakdown
- requests / retries / 429 / provider errors
- quota before/after or first/last safe headers
- normalized point count total
- point-count distribution: min, p10, median, p90, max
- zero-point / empty-session tickers
- earliest/latest timestamp distribution
- number of names ending before 16:00, 16:10, and 16:14 WIB
- identity/session validation failures
- storage size by raw/normalized/status/final artifact groups
- exact manifest SHA-256
- focused and full pytest results
- proof that no successful ticker was refetched on any resume

Also estimate the monthly request burden if this exact universe were captured for 20, 21, and 22 sessions, but do not authorize recurring capture from that estimate alone.

## Stop gate

After the broad census, STOP for independent ChatGPT review.

Explicitly not authorized:

- recurring scheduler/automation
- model/feature research
- Alpha, Path Risk, sizing, or execution work
- Open/TradingView work
- PIT-sector work
- Stockbit stream/sentiment collection
- portfolio/account access or order execution
- switching to Ultra or changing quota policy

# Stockbit Intraday Forward Capture — Frozen Implementation Spec

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/stockbit-intraday-forward-capture-v1`
Base: `dda3cb1ca7ed455e1cb932c093639723e4d3ea82`

## Decision

`STOCKBIT_INTRADAY_FORWARD_CAPTURE_IMPLEMENTATION_AUTHORIZED_NOT_RUNTIME_AUTHORIZED`

Prepare a fail-closed forward collector for Zapi `finance:stockbit/chart` without performing a live universe capture in this implementation task. This lane is independent from the ongoing historical Open recovery work.

## Current provider contract

Official Zapi documentation checked 2026-08-11 documents:

- endpoint: `GET /v1/finance:stockbit/chart`
- required parameter: `symbol`, e.g. `BBCA`
- optional `count`: keep only the last N points; omitting it returns the whole session
- response: one intraday point per trading minute
- point fields: `time`, `price`, `change`, `changePercent`
- response metadata includes `symbol`, `provider=stockbit`, `interval=intraday`, `timeframe=today`, `tradingDate`, `previousClose`
- endpoint cache TTL: 60 seconds

This is a price-path dataset, not OHLCV minute bars. Do not invent minute volume, bid/offer, OHLC, or trade fields that are not returned.

## Purpose

Create infrastructure to preserve Stockbit intraday price paths forward, for possible future Path Risk, execution, and intraday-alpha research. Collection does not authorize any feature/model use.

## Capture policy

- One chart request per ticker per capture run.
- Omit `count` so the full session is requested.
- API key only from environment variable `ZAPI_API_KEY`; never print or persist it.
- Default to a conservative request budget and require explicit execution.
- No retry storms. Only bounded transient retries.
- Preserve complete raw response plus normalized minute rows.
- Validate exact ticker identity, `provider=stockbit`, `interval=intraday`, `timeframe=today`.
- Require timestamps to parse, belong to exactly one trading date per ticker, and be unique after exact duplicate removal.
- Never forward-fill missing minutes or synthesize prices.
- Do not assume every clock minute exists; absence of a point is provider evidence, not a value to fill.
- A run is session-complete evidence only when captured after the configured Jakarta close-time gate. Earlier runs may only be explicitly marked `PARTIAL_SESSION`.
- On weekends/holidays or stale upstream output, if provider trading date differs from the expected Jakarta calendar date, classify the ticker as `NON_CURRENT_SESSION` rather than silently storing it as current-day data.
- Raw artifact roots are immutable. Refuse accidental overwrite.

## Universe policy

The collector must accept an explicit ticker list/file. This spec does not freeze a 300/400/500/full-universe policy yet. Universe selection is a separate decision after the first bounded pilot.

## Required implementation

Provide a CLI/module that supports at minimum:

- `--tickers` and/or `--tickers-file`
- `--output-root`
- `--expected-date` (default current Asia/Jakarta date)
- `--max-requests`
- `--capture-after` close-time gate (default 16:15 Asia/Jakarta)
- `--allow-partial-session` explicit override
- `--execute`; without it, dry-run only

Output artifacts should include:

- raw responses JSONL
- normalized minute rows CSV
- ticker status CSV
- run summary JSON
- manifest with SHA-256 for immutable artifacts

Status/report fields should include requests, retries, 429s, provider errors, successful ticker count, non-current-session count, partial-session count, normalized point count, earliest/latest timestamp, quota headers where available, and artifact hashes.

## Stop gate

Implementation and offline tests only. Do not start a 300/500/full-universe Stockbit capture from this spec. A bounded live pilot must be separately authorized after implementation review.

Do not touch the historical Open census branch, PIT-sector work, model/alpha code, or execution PnL.

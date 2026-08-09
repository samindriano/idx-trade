# Forward Open Archive V1

Date: 2026-08-10 (Asia/Jakarta)

## Purpose

Prevent future historical-Open gaps from recurring by archiving each new IDX session shortly after market close and catching up missed sessions when the Windows machine is next available.

This is a **data archival** facility only. It must not emit trading signals, orders, PnL claims, or promote execution-grade status by itself.

## Why this exists

The project proved that the old free public IDX Equity EoD archive has a post-2020 entitlement/retention boundary. Historical Open therefore cannot be assumed recoverable years later from the old public folders. The defensive operational answer is to archive permitted forward data while it is available.

## Scheduling contract

Target Windows Task Scheduler behavior:

- daily trigger: **22:00 Asia/Jakarta / local Windows time**;
- logon trigger: run the same catch-up command whenever the user next logs in;
- `StartWhenAvailable=true` so a missed 22:00 run is attempted after the machine becomes available;
- one instance at a time;
- recent lookback default: 45 calendar days;
- already archived session snapshots are immutable/idempotent and are not fetched again.

## Source gate

No price provider is frozen in this specification.

The runner intentionally requires an explicit audited provider adapter module exposing:

```python
SOURCE_ID = "..."

def fetch_session(session):
    return frame, metadata
```

The returned frame must contain:

- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

Until a separate Forward Open Acquisition source audit freezes an allowed provider, the scheduler **fails closed** with `BLOCKED_SOURCE_NOT_FROZEN`. It must never silently choose IDX scraping, Yahoo, Zapi, TradingView, Investing.com, or another source.

Direct crawling/scraping of `idx.co.id` remains prohibited under the existing source policy. A future provider adapter may only be added after source-specific access, terms, semantics, coverage, and provenance are reviewed.

## Session calendar

Expected recent sessions reuse the existing official IDX session-source implementation. Calendar evidence is recorded with each run. An unknown/malformed calendar source must fail rather than falling back to weekdays.

## Snapshot invariants

Each accepted session snapshot must:

- contain only the requested session date;
- have unique non-empty tickers;
- have positive Open/High/Low/Close;
- have non-negative Volume;
- satisfy `Low <= Open/Close <= High` and valid OHLC envelope;
- remain immutable after first successful archival.

Each successful session is stored under:

`<DATA_ROOT>/forward_open_archive/sessions/YYYY-MM-DD/`

with:

- `ohlcv.parquet`
- `manifest.json`

The manifest records provider identity/metadata, row/ticker counts, snapshot SHA-256, archive timestamp, and `execution_grade_promoted=false`.

The latest orchestration result is written to:

`<DATA_ROOT>/forward_open_archive/latest_run.json`

Runtime logs are written under:

`<DATA_ROOT>/forward_open_archive/logs/`

## Windows installation

Repository scripts:

- `scripts/run_forward_open_archive.ps1`
- `scripts/install_forward_open_archive_task.ps1`

Installation is a **local-machine operation** and cannot be completed from GitHub alone. Codex/local PowerShell may register the task only after verifying the exact checkout, Python environment, writable data root, and current user context.

It is acceptable to install the scheduler before the provider is frozen: it will fail closed and leave a durable `BLOCKED_SOURCE_NOT_FROZEN` status. Once an audited provider adapter is later supplied to the scheduled-task arguments, the same scheduler architecture becomes active without changing its archival invariants.

## Boundaries

This facility does not:

- repair the 2021-2026 historical Open gap;
- alter the immutable 1260 signal-research panel;
- modify Ranking V1/V2 labels/features/models;
- establish execution-grade certification;
- perform paper/live trading;
- place broker orders;
- authorize direct IDX scraping;
- authorize an unreviewed provider.

Historical backfill and forward archival remain separate tracks that may later feed a separately reviewed execution-data layer.

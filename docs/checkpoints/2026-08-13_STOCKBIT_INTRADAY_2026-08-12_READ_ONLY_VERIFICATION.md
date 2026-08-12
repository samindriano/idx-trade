# Stockbit Intraday 2026-08-12 Read-only Verification — 2026-08-13

Status: `CAPTURE_COMPLETE_WITH_EXPLICIT_TICKER_EXCEPTIONS`

This is a read-only inspection of the existing external Stockbit runtime. No
task was started, no provider was called, and no runtime data was changed.

## What was captured

The relevant task is `IDX-Trade Stockbit Intraday Daily`, not an EOD task. Its
2026-08-12 external session is:

- runtime root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\stockbit_intraday_recurring_v1`;
- expected date: `2026-08-12`;
- run mode: `SHADOW`;
- run summary: `complete=true`;
- task last result: `0` at `2026-08-12 18:33:13 +07:00`;
- final artifacts completed through approximately `18:46:40 +07:00`;
- `interval=intraday`, `timeframe=today`, provider `stockbit`;
- final rows: `111,695` across `835` unique tickers;
- timestamps: `2026-08-12 08:58` through `16:14` Asia/Jakarta.

This is therefore an intraday price-series capture for 12 August, not the
canonical EOD archive. Canonical EOD remains the separate IDX Stock Summary +
IDX Index Summary + Yahoo OHLCV runtime.

## Exact ticker outcomes

The final ticker-status artifact contains `962` attempted tickers:

| gate/status | count | interpretation |
|---|---:|---|
| `FETCH_TRADED` / `SUCCESS` | 835 | current-session intraday rows were archived |
| `FETCH_TRADED` / `NON_CURRENT_SESSION` | 1 | `SMBR`; provider returned 2026-08-11, not 2026-08-12 |
| `SKIP_NO_ACTIVITY` / `REQUEST_ERROR` `HTTP_404` | 126 | no-activity names; no 2026-08-12 rows archived |

The gate metadata expected `836` Stockbit fetches and `126` no-activity skips.
The run nevertheless attempted all `962` names, so the 126 no-activity names
received HTTP 404 responses rather than being avoided entirely. This is an
efficiency/behavior observation, not a claim that those names traded.

The run reported `unfinished_tickers=0`, `request_attempts=962`, zero retries,
zero HTTP 429 events, and no synthetic fill. `SMBR` is the only current-session
coverage exception and should remain explicit until a later normal run proves
the current date.

## Artifacts and hashes

- `final/run_summary.json`: `52dcb6bf1c73eb1031c6c735e53ab96f631d4dff821f96591283b61cbe91d7dc`;
- `artifact_manifest.json`: `9d8cd562fdc7eb5e57fe9609d42852858d94182078b61403dc645f4556cb076c`;
- `final/stockbit_intraday_rows.csv`:
  `58eb79a9625b6832a1cf87ef24b5264f5149c3edf81fd538eb86ba9c5d978034`;
- `final/stockbit_intraday_ticker_status.csv`:
  `6e118c68936c3042620989fef9d976401245bfd241212bee3d782717621bf344`;
- `gate/traded_today_decisions.csv`:
  `e9cd94b0a08eb760965b9f6bce4298bf7762ebf3f7c6c51a4152e06afc9d9b05`;
- `gate/gate_metadata.json`:
  `61394ec737d4f15f46a4fa246f78c24b9d4068aba4f7b31b0c0149882e401b24`;
- `day_metadata.json`:
  `6730d4dea65d8e0f0e49341109bd08107cfd0f631df4c3a332a1cd88dd8b2a46`.

The manifest contains `2,642` listed files, including final rows/status,
Stock Summary gate raw/normalized data, per-ticker raw/status/row artifacts,
and the universe snapshot.

## Policy state

The Stockbit policy remains `SHADOW`, not certified/enforced. The run recorded
one shadow false positive and zero false negatives; no synthetic fill was used.
This verification does not promote the policy and does not touch O2,
Reliability V1, outcomes, or the canonical EOD contract.

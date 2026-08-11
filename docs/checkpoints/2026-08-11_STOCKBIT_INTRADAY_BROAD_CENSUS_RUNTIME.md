# Stockbit Intraday Broad Census Runtime

Date: 2026-08-11 (Asia/Jakarta)  
Branch: `data/stockbit-intraday-forward-capture-v1`  
Starting remote HEAD: `a14fc8f32cca2212949c6112c55b0c8a14c5324e`  
Decision: `STOCKBIT_INTRADAY_20260811_CURRENT_UNIVERSE_BROAD_CENSUS_COMPLETE_STOP_FOR_REVIEW`

## Scope and authorization

This runtime executed only the frozen 2026-08-11 current-universe Stockbit
intraday census. It did not start recurring capture, Open/TradingView work,
PIT-sector work, modelling, feature research, execution PnL, or trading.

The run used the existing resumable farm, one request per frozen ticker,
`timeframe=today`, no `count`, no partial-session mode, expected date
`2026-08-11`, close gate `16:15`, `max_new_tickers=1200`, and monthly quota
reserve `3000`.

External immutable artifact root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\stockbit_intraday_broad_census_v1_20260811`

## Validation before runtime

- Focused farm tests: **8 passed**.
- Full pytest: **275 passed**.
- `ZAPI_API_KEY` was present; its value was never printed, persisted, or logged.
- Local Jakarta time was after the `16:15` complete-session gate.
- The output root did not exist before the run.

One implementation-only defect exposed by the focused test was fixed before
runtime. The recursive manifest now excludes `run_summary.json`; otherwise the
summary's own manifest digest changed the manifest and made the returned and
stored digests inconsistent. No capture or admission semantics changed.

## Frozen universe

- Source: `IDX_CURRENT_ACTIVE_STOCK_LIST`, fetched through the existing
  official IDX active-list provider.
- Expected date: `2026-08-11`.
- Frozen ticker count: **962**.
- Ticker-list SHA-256:
  `fe131ec56913ce232382c4220cfb61649b334ea42fe2180f5f585ab414825613`.
- Universe snapshot SHA-256:
  `5086d4f36a540fcc427134f97d696d030acce7268c1a6715a1929d2ba7be3a97`.
- The historical 979-ticker panel was not used as the capture universe.

## Capture result

- Attempted: **962**.
- Successful: **832**.
- Unfinished: **0**.
- Status breakdown: `SUCCESS=832`, `REQUEST_ERROR=130`.
- Request errors: `HTTP_404=130`.
- Request attempts: **962**.
- Retries: **0**.
- HTTP 429 events: **0**.
- Provider/session/identity validation failures among returned payloads: **0**.
- All 832 returned payloads passed provider identity (`stockbit`), symbol,
  interval (`intraday`), timeframe (`today`), and trading-date validation.
- No successful ticker was refetched on resume. This was a fresh root:
  `prior_terminal_or_skipped=0`; all terminal outcomes were produced by the
  single frozen pass.

The 130 `HTTP_404` tickers produced no provider payload and were not retried or
silently converted to empty sessions. There were **0 successful zero-point
sessions** and no synthetic or forward-filled points.

## Preserved payload and normalized evidence

The raw envelope preserves `ticker`, `captured_at`, and the complete provider
payload. The unwrapped provider data schema was identical across successful
responses:

- response fields: `change`, `changePercent`, `count`, `interval`, `items`,
  `previousClose`, `provider`, `symbol`, `timeframe`, `tradingDate`;
- timed item fields: `change`, `changePercent`, `price`, `time`;
- one untimed reference item was present in each of the 832 successful raw
  payloads and was excluded from normalized timed rows;
- timed duplicate rows: **0**;
- no minute filling, OHLCV invention, or timestamp interpolation was used.

Normalized points: **117,064**.

Point-count distribution across successful tickers:

| statistic | points |
|---|---:|
| min | 1 |
| p10 | 11 |
| median | 115 |
| p90 | 321 |
| max | 335 |

Timestamp distribution across successful tickers:

- earliest first point: `2026-08-11T08:58:00+07:00`;
- latest last point: `2026-08-11T16:14:00+07:00`;
- names ending before 16:00: **97**;
- names ending before 16:10: **466**;
- names ending before 16:14: **666**.

These are observed provider timestamp distributions, not claims of complete
clock-minute coverage.

## Quota and request safety

The previous pilot's final safe header is the pre-run baseline; the farm did
not persist its first response header separately. No separate quota probe was
made. Safe baseline to final response:

| header | baseline | final |
|---|---:|---:|
| rate limit / minute | 2000 | 2000 |
| remaining / minute | 1986 | 1946 |
| rate limit / month | 25000 | 25000 |
| remaining / month | 23562 | 22482 |

Final response also reported `http_status=200`, `retry_after=null`, and
`plan_expired_present=false`. The provider's remaining-month change was 1080
while the farm made 962 chart requests; no one-request-to-one-quota-unit
assumption is made.

Estimated monthly chart-request burden if this exact 962-ticker universe were
captured once per session:

- 20 sessions: **19,240** requests;
- 21 sessions: **20,202** requests;
- 22 sessions: **21,164** requests.

This estimate does not authorize recurring capture.

## Artifact sizes and hashes

| group | files | bytes |
|---|---:|---:|
| raw per-ticker | 832 | 17,858,167 |
| normalized per-ticker | 832 | 13,285,992 |
| status per-ticker | 962 | 319,630 |
| final consolidated | 3 | 13,281,890 |

| artifact | SHA-256 |
|---|---|
| `day_metadata.json` | `f690d29754fbe72ed1108b821a9d24659bfff8e0305116605d519401ec708891` |
| `universe_snapshot.csv` | `5086d4f36a540fcc427134f97d696d030acce7268c1a6715a1929d2ba7be3a97` |
| `final/run_summary.json` | `2b958763bfafc3bb9085f701b063ff19dc760d52c344df3efd15728857efa8c9` |
| `final/stockbit_intraday_rows.csv` | `4122d53104def4f696f3036d6a283497bb1d9965abb32f55bb53f2d9223c659c` |
| `final/stockbit_intraday_ticker_status.csv` | `033e38f32fa0d9189a073d9775037a9bcaa3d29f8cab62ef276fa532efe23481` |
| `artifact_manifest.json` | `c59949645e88e71fb72c5bbec53fca43b0ef1d62dd70f3960299b3d695a9807a` |

## Stop decision

The bounded broad census is complete and reproducible for the frozen
2026-08-11 universe. The result is **STOP_FOR_INDEPENDENT_CHATGPT_REVIEW**.
Recurring 300--500 or full-universe scheduling remains unauthorized.

# Stockbit Intraday Live Pilot Runtime

Date: 2026-08-11 (Asia/Jakarta)  
Branch: `data/stockbit-intraday-forward-capture-v1`  
Starting HEAD: `4117c2dadbe9271687c9814f1b0107f629839a93`  
Decision: `STOCKBIT_INTRADAY_BOUNDED_LIVE_PILOT_COMPLETE_STOP_FOR_REVIEW`

## Scope and controls

The exactly frozen 12-ticker post-close pilot ran once per ticker:

`BBCA, BBRI, BMRI, BBNI, TLKM, ASII, AMRT, ICBP, INDF, UNTR, ANTM, MDKA`

The collector used `GET /v1/finance:stockbit/chart` with only
`symbol=<ticker>` and omitted `count`, as required for the whole-session
contract. It ran at `2026-08-11T22:49:34.841496+07:00`, after the `16:15`
Asia/Jakarta close gate, with `--allow-partial-session` **not** set.

No Open/TradingView census, PIT-sector work, recurring capture, model/alpha,
Path Risk, execution feature, or execution-PnL work was started.

## Pilot result

| Metric | Result |
|---|---:|
| Requested tickers | 12 |
| Successful tickers | 12 |
| Non-current-session tickers | 0 |
| Partial-session tickers | 0 |
| Request-error tickers | 0 |
| HTTP requests/attempts | 12 |
| Retries | 0 |
| HTTP 429 events | 0 |
| Provider errors | 0 |
| Normalized points | 3,908 |
| Earliest normalized timestamp | `2026-08-11T08:58:00+07:00` |
| Latest normalized timestamp | `2026-08-11T16:14:00+07:00` |
| Session state | `SESSION_COMPLETE_WINDOW` |
| Synthetic fill | false |
| Minute volume | unavailable / not invented |

All 12 responses passed exact ticker identity, `provider=stockbit`,
`interval=intraday`, `timeframe=today`, provider trading date, and expected
date validation. All normalized timestamps were unique and monotonic. The
provider returned one initial reference item without `time` per ticker; these
12 items were excluded by the parser. No timed point had an invalid/nonpositive
price, no timestamp conflict occurred, and no duplicate exact normalized row
was dropped. Missing clock minutes were not filled.

The unwrapped payload schema was identical for all tickers:

- payload fields: `change`, `changePercent`, `count`, `interval`, `items`,
  `previousClose`, `provider`, `symbol`, `timeframe`, `tradingDate`;
- item fields: `change`, `changePercent`, `price`, `time`.

The normalized dataset therefore remains a price-path dataset only; it does not
contain invented minute OHLCV, volume, bid/offer, or trade fields.

## Per-ticker evidence

Every row below had status `SUCCESS`, provider session/metadata date
`2026-08-11`, identity/session validation PASS, 0 retries, 0 429s, 0 exact
duplicates, 1 untimed reference item excluded, and unique monotonic normalized
timestamps. `raw_payload_sha256` hashes the complete stored provider payload;
`normalized_rows_sha256` hashes that ticker's rows in the stored normalized CSV.

| Ticker | Raw items | Valid points | First | Last | Raw payload SHA-256 | Normalized rows SHA-256 |
|---|---:|---:|---|---|---|---|
| BBCA | 335 | 334 | 08:58 | 16:14 | `2cc70f6ebce3f7c02bf1856be960f0833ec37d5770826cea4895bbd97c5ae4b9` | `86181850c917601bc247afd6f7942136171d22b6c55251f5f4f7da3ab9599804` |
| BBRI | 336 | 335 | 08:58 | 16:14 | `c789ba663dfdef4ecdc692f82491e6c795ac80b436d88ea45f91bdf54c200d2e` | `34db5014fb4c827b9bfddb6e793d7db8e97e221bba880688390d8f5348c8ef6e` |
| BMRI | 336 | 335 | 08:58 | 16:14 | `944458576970e7cad8bdf0543fc2ba440f8a04144bb4e6c473224a6ebf85d47d` | `2ecc4fda55c09438c935ffa34a3b9abe21b5c2acccdc093fa06ec893b042e6df` |
| BBNI | 331 | 330 | 08:58 | 16:14 | `65efa3b91f1006756a7debbe19ee4766cf6f1547a0df91780c3810a5914de32d` | `d1e556e14b1f684ed5f1b493d4a15eebdaa2674f5d6d0edeae26207db74eaf22` |
| TLKM | 336 | 335 | 08:58 | 16:14 | `e50eb99f9e9b054b18189daff8c475f8a0e18eacd1d6909fa0ce245b5c2a7a36` | `dbcddf3a44cef203885b6a31b46ba6f0387bef57f3ba7083346c7533ea251382` |
| ASII | 336 | 335 | 08:58 | 16:14 | `eb21f89e8cf6387ed6367645f8c415b9414e4f594b7f1bf30bfb478ddc5fdc74` | `9717e9ff5e3bce5a3f303c862ace2ccf0c13ada4f1d5381a46239bf06440e34f` |
| AMRT | 318 | 317 | 08:58 | 16:14 | `aabe2ff237b6f40772525353365aca7b6e69a59160c748554f91ebfa993c9a0f` | `102abf20a370d3ef3fcf9b1050b62dc8395212846621f35d8c903850725e76e4` |
| ICBP | 297 | 296 | 08:58 | 16:09 | `69a0ea96bb8c63f8c26fb08859d91db9b03d40004c44fbef5e4692796ecfdb11` | `10f88ef3d10cd9bee094fadf9c477a82009ceb572cebba3be9aec65744229d31` |
| INDF | 314 | 313 | 08:58 | 16:14 | `76a95487366e28d083a6663498850c995f999d7b9ebec103690ff07bc8ed937d` | `6e5a81d5631bda254718066a6bcec85dc2d19ede9b835616f8b3463396a43081` |
| UNTR | 314 | 313 | 08:58 | 16:05 | `a783dacdf50c686606e360e300a35f4a0c7b32bd32d6651c96013a06f8c939d7` | `29db3f18abab5c7ad8e5d303507a21349a50ebe90aab02adc81e9c556e8be4f5` |
| ANTM | 336 | 335 | 08:58 | 16:14 | `a11a0ad419e48f7844f38393c1b23d868750032f2161b3ab6deb3e657f018d24` | `d791f374cd5e390107e5d7860265a425039c2a3ca2d5ab40d9c6f387c5673049` |
| MDKA | 331 | 330 | 08:58 | 16:14 | `a9a517bade8cd1dedfc61447457f11a16d1ddaf877a7d2ace5faaff27b79241c` | `41535dc5fb82d37c5f312cd9806960da44121c8dfbd1102a372ae4ab37833fb0` |

## Quota, artifacts, and validation

Safe quota headers were captured from the first and last chart responses:

- first response: HTTP 200, minute `limit=2000`, `remaining=1999`, month
  `limit=25000`, `remaining=23575`, no `Retry-After`, no plan-expired header;
- last response: HTTP 200, minute `limit=2000`, `remaining=1986`, month
  `limit=25000`, `remaining=23562`, no `Retry-After`, no plan-expired header.

The API key was read only from `ZAPI_API_KEY`; it was not printed, persisted,
or committed.

- External immutable artifact root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\stockbit_intraday_live_pilot_v1_20260811`
- Artifact manifest SHA-256:
  `bfb3630ad64c7d0c6d08c77fec52738b16423e7edfe3b95443615387e0a06aef`
- `stockbit_intraday_raw_responses.jsonl`:
  `2c9693404454345a20f62355e1fb31bf15beaa9df3999fd2d08883102dcd26aa`
- `stockbit_intraday_rows.csv`:
  `fe40ac6ab76a77397560da32a930d6a3241782cc5847bd581582edcd0deb7e73`
- `stockbit_intraday_ticker_status.csv`:
  `58c9e8a9fa0a27b198c474f88437c2e6b9dde7d92ce7f4ab57c1d30c10c0602`
- `run_summary.json`:
  `c3f40a6d050c65ef4493e0a98f8faaf8c086ddc478ee540839810ecea92407b3`

Validation on this branch:

- focused Stockbit tests: **9 passed**;
- full pytest: **267 passed**;
- no implementation change was required after the tests;
- pilot result is evidence collection only and does not authorize recurring
  300–500 ticker capture.

Stop for independent ChatGPT review before any recurring-universe or research
use authorization.

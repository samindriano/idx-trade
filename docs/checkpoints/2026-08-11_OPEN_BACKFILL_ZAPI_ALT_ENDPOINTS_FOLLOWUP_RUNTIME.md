# Zapi Alternative-Endpoint Quota-Aware Follow-up Runtime

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-alt-endpoints-audit-v1`
Review base: `3fa6aee15d1b06f2d62055efee869a7ef1d436e7`

## Decision

`ZAPI_ALT_OPEN_FOLLOWUP_COMPLETE`; stop for independent ChatGPT review.
TradingView follow-up was fail-closed by an unknown 429 quota window after one
request. Investing was not called because quota status was not clear.

No bulk backfill, panel write, execution-grade promotion, corporate-action
repair, modelling, Ranking/PIT-sector work, execution PnL, paper/live trading,
broker integration, or main merge was performed.

## Frozen integrity

- API key was visible to the process; its value was never printed, persisted,
  hashed, or committed.
- Frozen sample: 240 rows / 206 tickers.
- Sample SHA-256:
  `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`.
- Prior runtime manifest SHA-256:
  `b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80`.
- Immutable panel SHA-256 before/after:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.
- Focused tests after implementation: 9 passed.
- Full pytest after implementation: 251 passed, exit 0; 5 existing warnings.

## Offline TradingView candidate breakdown

The existing 61 accepted candidates were read without network access and
written to `tradingview_candidate_breakdown.csv`.

- By frozen sample role: `RESIDUAL_PROVIDER_GAP=37`,
  `RESIDUAL_HLC_MISMATCH=24`.
- By year: 2021=`10`, 2022=`18`, 2023=`20`, 2024=`13`.
- Ticker concentration: `HKMU=5`; `BAYU=2`, `CBMF=2`, `JSKY=2`; every
  other candidate ticker has one row.
- Full deterministic ticker/date/reason breakdown is in the external
  follow-up artifact, not committed to Git.

## Quota-aware implementation

The request layer now records, for every HTTP 429, only:

- JSON `window` when it is exactly `minute` or `month`;
- `Retry-After`;
- `X-RateLimit-Limit`;
- `X-RateLimit-Remaining-Minute`;
- `X-RateLimit-Remaining-Month`;
- presence of `X-Plan-Expired`.

Response bodies and secrets are not persisted. `window=minute` retries with a
bounded wait, `window=month` stops immediately, and an unknown window stops
after the first diagnostic rather than burning repeated retries.

The follow-up loader also accepts empty prior CSV artifacts, and the offline
breakdown/combined summary preserve prior evidence without overwriting the
prior runtime directory.

## TradingView follow-up

- Prior terminal `RATE_LIMITED` tickers selected: `71`.
- Prior successful tickers refetched: `0`.
- Actual follow-up network requests: `1`.
- Follow-up retries: `0`.
- Rate-limit events: `1`.
- First selected ticker: `MAIN`.
- Response classification: `HTTP_429`, `window=unknown`,
  `UNKNOWN_QUOTA_WINDOW` stop.
- Captured metadata: `remaining_minute=100`, `remaining_month=0`,
  `Retry-After` absent, `X-RateLimit-Limit` absent,
  `X-Plan-Expired` absent.
- New provider rows: `0`.
- Remaining selected rate-limited tickers not called: `70`.
- Combined provider rows remain the prior `130,044`.
- Combined exact sample dates remain `101/240`.
- Combined H/L/C exact remains `84/240`.
- Combined known-control H/L/C exact remains `23/40`.
- Combined known-control Open exact remains `23/40`.
- Combined recovery candidates remain `61`.
- No prior successful ticker was refetched.

The unknown window was not inferred as either minute or month. Per the
fail-closed rule, no further TradingView retry was attempted.

## Investing follow-up

- Follow-up attempted: `false`.
- Skip reason: `TRADINGVIEW_QUOTA_STATUS_NOT_CLEAR`.
- Historical requests: `0`.
- Combined identity evidence retains the prior `206 RATE_LIMITED` rows;
  verified identities remain `0`.
- Combined provider rows and recovery candidates remain `0`.

## Artifacts and integrity

Final follow-up artifacts are outside Git under the external
`open_backfill_zapi_alt_endpoints_followup_v1_20260811` runtime directory.
The first three pre-network failed attempts and the prior summary-correction
attempt were preserved in separate external `_pre_*` directories.

Final artifact manifest SHA-256:
`87e40d23e02f7557d8a90120577ff68fd3e3567ee339c856386c141fdb61802d`

| Artifact | SHA-256 |
|---|---|
| `artifact_manifest.json` | `87e40d23e02f7557d8a90120577ff68fd3e3567ee339c856386c141fdb61802d` |
| `tradingview_candidate_breakdown.csv` | `57d184314512b4818a3ac2cfcb1ff3f1f37ae2ebd610c294cb34c36a6c63e9ca` |
| `tradingview_followup_candidate_rows.csv` | `0ab643a79499728a6992df85fe74c9cdf182b285b8ad3b59668569033d7049a0` |
| `tradingview_followup_ticker_status.csv` | `25ab7928003c8e619a6eeb3040af4675e8396f9b49f61c0e72635ee9de55b77e` |
| `tradingview_followup_rate_limit_diagnostics.csv` | `9f8f36a02afc5232df2e2d113523d89e33f93311d56f40cb9023f752374cc5f7` |
| `tradingview_combined_candidate_rows.csv` | `294896a1c052871d36e8d275b696cd2e8521b490d5da18e3da713c47675e20de` |
| `tradingview_combined_ticker_status.csv` | `7350aaaf409db3c1c4ebcfc7fff60e65a972d29c7ee29b8cdf8662cdeb82f0be` |
| `tradingview_combined_row_audit.csv` | `0be3d56bce3c61f2e3ad2975bc852543dd37bc411651cb122eddde3769e2ea60` |
| `investing_followup_candidate_rows.csv` | `0ab643a79499728a6992df85fe74c9cdf182b285b8ad3b59668569033d7049a0` |
| `investing_followup_identity.csv` | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| `investing_followup_ticker_status.csv` | `b4d9620d9c4d35fbe04a484699fddbb40654f865930ff71a23ad5484820d0803` |
| `investing_followup_rate_limit_diagnostics.csv` | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| `investing_combined_candidate_rows.csv` | `0ab643a79499728a6992df85fe74c9cdf182b285b8ad3b59668569033d7049a0` |
| `investing_combined_identity.csv` | `17ddde3318bf6bf69a892a66928e4d4596bf34e59f10e48fc8c9cd577748579d` |
| `investing_combined_ticker_status.csv` | `b4d9620d9c4d35fbe04a484699fddbb40654f865930ff71a23ad5484820d0803` |
| `investing_combined_row_audit.csv` | `a0443ed42eb00f7f80bfa47834b3111fea6c325fedc4bba3ec63c0f291dbac9b` |
| `provider_overlap.csv` | `3dd044416462f1eda31bcc5f368e63fe8dcfcc04af85b20fd6c97c513a250d94` |
| `zapi_alt_open_followup_summary.json` | `a6b49848ab733037b94d7c64cf604cf7862d59611f3a8834c52a0cfa6e39e7a7` |

All manifest-listed hashes were rechecked and matched. Stop for independent
review.

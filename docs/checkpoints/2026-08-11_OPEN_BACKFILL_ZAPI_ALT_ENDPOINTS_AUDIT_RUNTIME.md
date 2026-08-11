# Zapi TradingView + Investing Alternative-Endpoint Audit Runtime

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-alt-endpoints-audit-v1`
Runtime base HEAD: `f28d14c10d98313cac923247c7eff5913c2d0f06`

## Decision

`ZAPI_ALT_OPEN_AUDIT_COMPLETE`; stop for independent ChatGPT review. Neither
provider is promoted to an Open-recovery source from this bounded audit.

## Preflight and frozen inputs

- `ZAPI_API_KEY`: present to the process; value was not printed, hashed,
  persisted, or committed.
- Focused tests before runtime: 5 passed.
- Full pytest before runtime: passed, exit 0.
- Focused tests after the bounded 404 fix: 6 passed.
- Full pytest after the bounded 404 fix: 248 passed, exit 0; 5 existing
  warnings.
- Sample: 240 rows, 206 unique tickers; roles were 120
  `RESIDUAL_HLC_MISMATCH`, 80 `RESIDUAL_PROVIDER_GAP`, and 40
  `KNOWN_CONTROL`.
- Frozen sample SHA-256:
  `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`.
- Immutable panel SHA-256 before and after:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Bounded implementation fix

The first runtime stopped at a single TradingView HTTP 404 (`FREN`) because
the shared status classifier treated every 4xx response as `ACCESS_DENIED`.
That is not a credential/plan gate for a symbol-level 404. The smallest
semantics-preserving fix classifies HTTP 404 as `REQUEST_ERROR`, allowing the
frozen per-ticker audit to continue. A regression test verifies that a 404
does not stop the next sorted ticker.

The first runtime output was preserved outside Git at:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_audit_v1_20260811_pre_404_fix`

The final runtime output is at:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_audit_v1_20260811`

## TradingView

- Access: `ACCESSIBLE`.
- Plan: `EMPIRICALLY_REACHED`.
- Unique ticker attempts: 206/206.
- Requests made: 348; retries: 142; rate-limit events: 213.
- Ticker status: 134 `SUCCESS`, 71 `RATE_LIMITED`, 1 symbol/provider
  `REQUEST_ERROR` (`FREN` HTTP 404).
- Provider rows: 130,044.
- Exact ticker/date sample coverage: 101/240 (42.1%).
- History-window unavailable: 50 rows.
- H/L/C exact: 84/240 (35.0%).
- Known-control H/L/C exact: 23/40 (57.5%).
- Known-control Open exact: 23/40 (57.5%).
- Positive/in-range missing-Open candidates: 61.
- Recovery candidates: 61.
- Yahoo mismatch arbitration among 120 rows: 24 support the certified
  panel, 3 support Yahoo, 12 are provider-vs-both disagreements, and 84 have
  no usable provider row (including history-window/provider-error rows).
- Class histogram: `TV_HISTORY_WINDOW_UNAVAILABLE=50`,
  `TV_HLC_DISAGREEMENT=17`, `TV_IDENTITY_OR_PROVIDER_ERROR=89`,
  `TV_PANEL_HLC_OPEN_EXACT_CONTROL=23`, `TV_RECOVERY_CANDIDATE=61`.

## Investing

- Access: `ACCESSIBLE`.
- Plan: `EMPIRICALLY_REACHED`; no plan-gate response was observed.
- Search requests made: 618 total attempts for 206 tickers; retries: 412;
  rate-limit events: 618.
- Search identity status: 206 `RATE_LIMITED`; verified, ambiguous, and
  not-found identity counts are all zero because search never returned a
  usable response.
- Historical requests: 0; no identity was eligible to advance.
- Provider rows: 0.
- Exact ticker/date coverage: 0/240.
- H/L/C exact: 0/240; known-control H/L/C exact: 0/40; known-control Open
  exact: 0/40; recovery candidates: 0.
- Class histogram: `INV_PROVIDER_ERROR=240`.
- All 206 recorded search errors were bounded `HTTP_429:RATE_LIMITED`.

## Cross-provider and gate result

- Rows covered by both providers: 0.
- Exact raw OHLC agreement on overlap: 0.
- TradingView Yahoo-H/L/C support count: 3; Investing: 0.
- `execution_grade_promoted=false`.
- `bulk_backfill_authorized=false`.
- `corporate_action_repair_performed=false`.
- No panel write, bulk backfill, corporate-action repair, modelling, Ranking,
  PIT-sector work, execution PnL, or main merge was performed.

## Artifact hashes

Final runtime artifact manifest SHA-256:
`b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80`

| Artifact | SHA-256 |
|---|---|
| `artifact_manifest.json` | `b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80` |
| `investing_candidate_rows.csv` | `0ab643a79499728a6992df85fe74c9cdf182b285b8ad3b59668569033d7049a0` |
| `investing_identity.csv` | `17ddde3318bf6bf69a892a66928e4d4596bf34e59f10e48fc8c9cd577748579d` |
| `investing_row_audit.csv` | `a0443ed42eb00f7f80bfa47834b3111fea6c325fedc4bba3ec63c0f291dbac9b` |
| `investing_ticker_status.csv` | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| `provider_overlap.csv` | `3dd044416462f1eda31bcc5f368e63fe8dcfcc04af85b20fd6c97c513a250d94` |
| `tradingview_candidate_rows.csv` | `5e9b7284629267ba0e04abfb02a95272cb0828c85b35354ff594b75962e78a10` |
| `tradingview_row_audit.csv` | `1e6583ae739c58a8b513fe93d564bdcfbf4bc31428733d293941f40d71ab6052` |
| `tradingview_ticker_status.csv` | `7350aaaf409db3c1c4ebcfc7fff60e65a972d29c7ee29b8cdf8662cdeb82f0be` |
| `zapi_alt_open_summary.json` | `a1e33bca14088f96101011094f4e5f3dc12650c79ece457e751bb1c9bfeaca35` |

The manifest-listed artifact hashes were rechecked and all matched. Stop for
independent ChatGPT review.

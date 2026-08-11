# Historical Open Backfill — Zapi Alternative Endpoints Audit V1

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-alt-endpoints-audit-v1`
Parent review commit: `fa39fb576516d91265cc884d437b60d8d8415b1a`

## Decision

**`ZAPI_TRADINGVIEW_INVESTING_BOUNDED_AUDIT_AUTHORIZED`**

The prior Zapi `finance:idx/stock-summary` endpoint is rejected as an Open-recovery source, but that result does not reject every Zapi upstream. A bounded audit of the separate TradingView and Investing.com historical OHLC endpoints is authorized.

No bulk backfill, execution-grade promotion, corporate-action repair, modelling, Ranking/PIT-sector work, execution PnL, paper/live trading, broker integration, or main merge is authorized.

## Prior-history check

Repository code/file/commit/branch searches on 2026-08-11 found no persisted historical experiment or checkpoint explicitly naming `Investing.com`, `investpy`, or `TradingView` as an IDX historical-Open source. Cross-chat context retrieval likewise did not recover an older factual rejection reason. Therefore there is no preserved prior decision that can safely be inherited. Any remembered older attempt is treated as undocumented rather than silently repeated or contradicted.

## Current endpoint evidence

### TradingView via Zapi

Endpoint: `GET /v1/finance:tradingview/chart`

Current Zapi documentation explicitly supports:

- `market=indonesia`;
- exchange-qualified symbols such as `IDX:BBCA`;
- `resolution=1D`;
- daily OHLCV candles with a positive `open` field in examples;
- `count` default 200, maximum 1000.

Important limitation: the documented endpoint exposes no historical anchor/pagination parameter. A sample date older than the latest 1000 returned candles must be classified as `HISTORY_WINDOW_UNAVAILABLE`, not as bad price semantics.

### Investing.com via Zapi

Endpoints:

- `GET /v1/finance:investing/search`
- `GET /v1/finance:investing/historical`

Current documentation explicitly exposes OHLCV historical candles with:

- `interval=1d`;
- `period` in `1d|1w|1mo|1y|5y|max`;
- optional `pointscount`;
- an internal `pairId` override.

Bare ticker resolution is not trusted. Each ticker must first be identity-resolved through Investing search. Historical data may be evaluated only when exactly one candidate can be defensibly tied to the Indonesian/Jakarta listing by ticker plus exchange/country metadata. Ambiguous or non-Indonesian matches fail closed.

## Frozen sample

Reuse the exact outcome-independent sample from the completed Zapi stock-summary audit:

- rows: `240`;
- unique tickers: `206`;
- roles:
  - `RESIDUAL_HLC_MISMATCH = 120`;
  - `RESIDUAL_PROVIDER_GAP = 80`;
  - `KNOWN_CONTROL = 40`;
- sample SHA-256:
  `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`.

Do not reselect rows after observing either provider.

Runtime may read the existing external sample manifest from the prior Zapi output root. It must verify the exact sample SHA before any provider call.

## Frozen price-admission contract

For each provider and exact ticker/date row:

1. identity must be valid for the Indonesian security;
2. session date must match exactly after timezone-aware conversion to Asia/Jakarta session date;
3. raw High equals certified panel High exactly;
4. raw Low equals certified panel Low exactly;
5. raw Close equals certified panel Close exactly;
6. raw Open is finite and `> 0`;
7. raw Open lies within `[certified Low, certified High]`;
8. existing non-null panel Open is never overwritten;
9. known controls report exact Open agreement.

No price adjustment, ratio fitting, source averaging/voting, previous-Close substitution, interpolation, forward fill, synthetic Open, or inferred corporate-action factor is allowed.

## Provider-specific classifications

### TradingView

For a requested sample row classify one of:

- `TV_PANEL_HLC_OPEN_EXACT_CONTROL`
- `TV_PANEL_HLC_ONLY_CONTROL`
- `TV_RECOVERY_CANDIDATE`
- `TV_PANEL_HLC_MATCH_OPEN_REJECTED`
- `TV_HLC_DISAGREEMENT`
- `TV_HISTORY_WINDOW_UNAVAILABLE`
- `TV_IDENTITY_OR_PROVIDER_ERROR`

For Yahoo H/L/C mismatch rows additionally report whether TradingView supports the certified panel or Yahoo when both values are available.

### Investing

Identity resolution first classifies:

- `INVESTING_IDENTITY_VERIFIED`
- `INVESTING_IDENTITY_AMBIGUOUS`
- `INVESTING_IDENTITY_NOT_FOUND`

Only verified identities may call/evaluate historical data. Row classifications then mirror the TradingView price contract:

- `INV_PANEL_HLC_OPEN_EXACT_CONTROL`
- `INV_PANEL_HLC_ONLY_CONTROL`
- `INV_RECOVERY_CANDIDATE`
- `INV_PANEL_HLC_MATCH_OPEN_REJECTED`
- `INV_HLC_DISAGREEMENT`
- `INV_HISTORY_WINDOW_UNAVAILABLE`
- `INV_PROVIDER_ERROR`

## Request budget and rate discipline

The sample contains 206 unique tickers. Maximum intended requests:

- TradingView chart: at most 206 requests;
- Investing search: at most 206 requests;
- Investing historical: at most 206 requests, and only for verified identities;
- total intended maximum: 618 billable requests.

Stay well below current free-tier minute limits using serial requests and a conservative delay. Honor HTTP 429/Retry-After. Do not bypass provider limits, rotate keys, parallelize network calls, or widen the request budget.

TradingView uses `count=1000`, `resolution=1D`, `market=indonesia`, and exchange-qualified `IDX:<ticker>`.

Investing uses verified `pairId`, `interval=1d`, `period=max`, and a frozen requested `pointscount=1500`. If the endpoint rejects this specific `pointscount` as invalid, STOP for review rather than silently changing the request shape after observing results.

## Required outputs

For each provider report:

- access/plan status;
- requests, retries, 429s, and errors;
- ticker identity coverage;
- sample exact ticker/date coverage;
- history-window unavailable rows;
- H/L/C exact count/rate;
- known-control Open exact count/rate;
- missing-Open rows with positive/in-range Open;
- fully admissible recovery candidates;
- rejection histogram;
- Yahoo mismatch arbitration counts;
- provider/raw artifact hashes.

Also report overlap where both providers cover the same sample row and whether their raw OHLC agree.

## Decision gate

Neither provider advances to targeted historical recovery unless it demonstrates all of:

1. defensible IDX identity;
2. strong known-control H/L/C agreement;
3. strong known-control Open agreement;
4. at least some genuinely additional missing-Open recovery under the unchanged gate;
5. no systematic adjusted/raw or session-date mismatch.

A provider that has good H/L/C but missing/zero Open may remain a corroborator, but does not become an Open source.

## Stop boundary

After the bounded TradingView + Investing audit, write factual runtime documentation and STOP for independent ChatGPT review.

Do not fill the derivative panel, run a full-universe provider census, alter corporate-action evidence, shorten the execution window, change the universe, or start downstream research merely because one pilot looks promising.

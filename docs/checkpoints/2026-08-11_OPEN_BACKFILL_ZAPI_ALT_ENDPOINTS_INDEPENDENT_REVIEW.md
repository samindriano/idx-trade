# Zapi Alternative Endpoints Audit — Independent Review

Date: 2026-08-11 (Asia/Jakarta)
Reviewed branch: `data/idx-open-backfill-zapi-alt-endpoints-audit-v1`
Reviewed runtime commit: `5165bdf8dd98b494217894b6d426b8c0b717b958`

## Decision

**`TRADINGVIEW_PROMISING_INCOMPLETE_INVESTING_UNASSESSED_RATE_LIMIT_DIAGNOSTIC_AUTHORIZED`**

The bounded runtime is accepted as factual evidence, but it is not a final provider verdict because rate-limit contamination materially reduced coverage. TradingView is promising for raw historical Open recovery; Investing remains unassessed rather than rejected.

No bulk backfill, execution-grade promotion, corporate-action repair, modelling, Ranking/PIT-sector work, execution PnL, paper/live trading, broker integration, or main merge is authorized.

## Integrity accepted

- frozen sample unchanged: `240` rows / `206` tickers;
- sample SHA-256: `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`;
- immutable panel SHA before/after unchanged: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- focused tests: `6 passed`;
- full suite: `248 passed`, `5 existing warnings`;
- final artifact manifest SHA: `b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80`;
- HTTP 404 classifier correction is accepted as a bounded semantics fix: a symbol-level 404 is provider/symbol failure, not credential or plan denial.

## TradingView review

Observed:

- `206` tickers attempted;
- `134` successful ticker responses;
- `71` terminal rate-limited tickers;
- `1` symbol/provider 404 (`FREN`);
- `101 / 240` exact sample ticker/date rows;
- `84 / 240` H/L/C exact;
- known-control H/L/C exact: `23 / 40`;
- known-control Open exact: `23 / 40`;
- `61` rows satisfied the unchanged missing-Open recovery gate;
- `50` sample rows were outside the returned 1000-candle history window;
- Yahoo-mismatch sample arbitration among covered rows included `24` supporting certified panel, `3` supporting Yahoo, and `12` disagreeing with both.

Interpretation:

TradingView demonstrates genuine additional Open evidence under the unchanged gate. This is materially stronger than the rejected Zapi `stock-summary` endpoint, which produced zero admissible missing-Open recovery in its frozen audit.

However, this runtime is not sufficient to authorize bulk recovery because coverage is selection-contaminated by terminal rate limiting, and the 1000-candle endpoint window structurally cannot cover the oldest sample dates. The `61` accepted candidates must be preserved as evidence, but not extrapolated to the unresolved universe.

Before any promotion, produce an offline breakdown of those `61` candidates by frozen sample role (`RESIDUAL_PROVIDER_GAP` versus `RESIDUAL_HLC_MISMATCH`), ticker, and year. No network call is required for that breakdown.

## Investing review

Investing is **not rejected**.

All `206` identity searches terminated as HTTP 429, so:

- zero identities were actually evaluated;
- zero historical requests were made;
- zero price rows were observed;
- zero Open-recovery quality evidence exists.

The current runner records all HTTP 429 responses only as generic `RATE_LIMITED`. Current Zapi documentation distinguishes per-minute and per-month rate-limit windows, and exposes rate-limit/quota headers. Therefore the runtime cannot determine whether the Investing result reflects a temporary minute window, monthly quota exhaustion, or another provider-specific throttling state.

## Concrete runtime gap

Before another provider call, the request layer must capture on every HTTP 429 without exposing credentials:

- JSON `window` (`minute` or `month`) when present;
- `Retry-After`;
- `X-RateLimit-Limit`;
- `X-RateLimit-Remaining-Minute`;
- `X-RateLimit-Remaining-Month`;
- `X-Plan-Expired` presence only.

Behavior must become fail-closed by rate-limit class:

- `window=minute`: honor the provider reset/retry timing with a bounded retry;
- `window=month`: stop the provider immediately; do not burn repeated retries;
- unknown 429: stop after minimal bounded evidence rather than retrying hundreds of times.

Do not change price admission, provider identity, sample selection, or source semantics while making this diagnostic correction.

## Authorized follow-up

A single follow-up stage is authorized after the rate-limit diagnostic correction and tests:

1. perform offline analysis of the existing TradingView artifacts, especially the `61` recovery candidates by sample role/year;
2. capture quota-window diagnostics before meaningful provider rerun;
3. retry TradingView only for the `71` tickers whose final status was `RATE_LIMITED`; do not refetch the `134` successful tickers or the FREN 404;
4. retry Investing identity search only if quota diagnostics show requests can validly proceed;
5. for Investing, historical requests remain limited to identities that pass the already-frozen Indonesia/Jakarta verification contract;
6. merge follow-up evidence with the immutable first-run artifacts without overwriting them;
7. stop for independent review again.

No full-universe census or panel write is authorized.

## Promotion gate remains unchanged

TradingView or Investing may advance only if, after rate-limit-complete evidence:

- identity/session semantics remain defensible;
- known-control H/L/C and Open agreement are strong;
- meaningful missing-Open recovery persists;
- no systematic adjustment/session-date issue appears;
- recovered rows still pass exact certified H/L/C + finite positive in-range raw Open;
- existing Open is never overwritten.

## Stop boundary

Stop after the quota-aware completion audit. Do not weaken admission rules or interpret unavailable/rate-limited rows as no-trade/suspension. Do not start downstream execution PnL or modelling from the current partial TradingView sample.

# Zapi TradingView Resume — Frozen Spec

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-tradingview-resume-v1`
Base: `d7114df0bdbc4e1ecaacb0091a3b84772d4391e1`
Decision: `ZAPI_PRO_TRADINGVIEW_RATE_LIMITED_RESUME_AUTHORIZED`

## Context

The prior Zapi TradingView audit preserved all successful evidence. The first audit attempted 206 unique tickers on the frozen 240-row sample and produced 134 TradingView successes, 71 rate-limited tickers, and 1 provider/symbol error (`FREN`). A quota-aware follow-up intentionally attempted only one previously rate-limited ticker, then stopped because the Free monthly quota was exhausted.

The user has now activated Zapi Pro. The Pro envelope was independently observed during the separate IDX stock-history audit as 25,000 requests/month and 2,000 requests/minute.

This experiment resumes only the unfinished TradingView portion. It must not refetch the 134 prior successful TradingView tickers and must not use the separate `finance:idx/stock-history` endpoint for Open recovery.

## Frozen sample and existing evidence

Reuse exactly the original 240-row sample and existing artifacts. Do not reselect sample rows.

- 120 `RESIDUAL_HLC_MISMATCH`
- 80 `RESIDUAL_PROVIDER_GAP`
- 40 `KNOWN_CONTROL`
- 206 unique tickers
- sample SHA-256: `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`

Prior successful TradingView evidence MUST be reused from the preserved artifact set rather than refetched.

Prior first-runtime root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_audit_v1_20260811`

Prior follow-up root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_followup_v1_20260811`

Known prior result:
- 134 TradingView successful tickers
- 71 prior `RATE_LIMITED` tickers
- 1 provider/symbol error (`FREN`)
- 61 recovery candidates already observed
- 23 known-control exact Open rows already observed
- 50 history-window-unavailable sample rows
- preserved TradingView candidate rows SHA-256: `5e9b7284629267ba0e04abfb02a95272cb0828c85b35354ff594b75962e78a10`
- preserved TradingView row audit SHA-256: `1e6583ae739c58a8b513fe93d564bdcfbf4bc31428733d293941f40d71ab6052`

## Authorized network scope

1. Verify the credential now exposes the Pro quota envelope before TradingView calls. Never print or persist the API key.
2. Load the exact prior ticker-status evidence and select ONLY tickers whose prior final TradingView status was `RATE_LIMITED`.
3. The expected retry set is 71 tickers from the original audit. If the existing follow-up already converted one of these into a terminal non-success state due monthly quota exhaustion, it remains eligible because no chart data was obtained.
4. Do NOT refetch any of the 134 prior `SUCCESS` tickers.
5. Do NOT broaden to full-universe residual census in this experiment.
6. Do NOT run Investing in this experiment. Investing remains a separate unassessed lane.
7. Do NOT retry `FREN` unless the existing artifacts show it was part of the 71 rate-limited set; its prior 404/provider-error state is not automatically authorized for retry.
8. Serial or safely bounded requests only. Respect live quota headers and stop on any unexpected plan/quota anomaly.

TradingView request contract remains frozen:
- endpoint: Zapi TradingView chart endpoint already implemented in the prior audit
- market: `indonesia`
- symbol: `IDX:<ticker>`
- resolution: `1D`
- count: `1000`

No request-shape expansion, undocumented pagination, historical-anchor experiments, or alternate symbol mapping is authorized here.

## Admission contract

For exact ticker/date, unchanged from the original audit:

1. requested ticker identity must match;
2. provider session date must match exactly;
3. raw High == certified panel High;
4. raw Low == certified panel Low;
5. raw Close == certified panel Close;
6. raw Open finite and > 0;
7. certified Low <= raw Open <= certified High;
8. known-control Open compared exactly;
9. no existing panel Open overwrite;
10. no adjusted-price substitution, split-factor inference, averaging/voting, previous-Close substitution, interpolation, forward fill, synthetic Open, or corporate-action inference.

If the requested sample date is older than the 1000-candle returned window, classify `HISTORY_WINDOW_UNAVAILABLE`; do not change the request after seeing the result.

## Merge rule

After retrying only the unfinished tickers, combine the newly obtained TradingView evidence with the preserved first-runtime TradingView evidence offline.

The combined result must be deduplicated by provider/ticker/date and must preserve provenance indicating whether each row came from the original run or the Pro resume run.

Do not overwrite the old artifact roots.

## Required report

Return both incremental and combined metrics:

### Incremental Pro-resume
- Pro quota before/after;
- selected ticker count and exact ticker list hash;
- requests/retries/429/provider errors;
- successful/failed ticker count;
- provider rows;
- exact sample-date coverage;
- H/L/C exact;
- known-control H/L/C exact and Open exact;
- missing-Open recovery candidates;
- history-window unavailable count;
- all classification counts.

### Combined original + resume
- confirm 134 prior successful tickers were not refetched;
- final TradingView ticker status across all 206 tickers;
- exact sample ticker/date coverage out of 240;
- H/L/C exact out of 240;
- known-control H/L/C exact and Open exact out of 40;
- missing-Open recovery candidates out of 200, split by `RESIDUAL_HLC_MISMATCH` / `RESIDUAL_PROVIDER_GAP` and year;
- Yahoo mismatch arbitration: supports certified panel / supports Yahoo / disagreement / unusable;
- history-window-unavailable count;
- provider/symbol errors;
- artifact hashes and manifest SHA;
- immutable panel SHA before/after.

## Gate

If the combined TradingView sample demonstrates strong exact known-control behavior and meaningful recovery under the unchanged gate, STOP and request independent ChatGPT authorization for a separate targeted/full residual census.

No panel write, bulk Open backfill, full-universe census, Investing audit, corporate-action repair, execution-grade promotion, modelling, PIT-sector work, or downstream execution PnL is authorized by this spec.

# TradingView Identity / Provider Remediation — Frozen Spec

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/idx-open-backfill-tradingview-identity-remediation-v1`
Base: `d26f9956f8c736a277a7108805376105e6cfedcf`
Decision: `TRADINGVIEW_IDENTITY_PROVIDER_REMEDIATION_AUDIT_AUTHORIZED`

## Accepted predecessor state

The Yahoo + accepted TradingView derivative is the active Open-backfill derivative:

- total rows: 981,940;
- unresolved Open: 43,801;
- Open coverage: 95.5393%;
- Yahoo fills: 397,367;
- accepted TradingView fills: 5,675;
- immutable panel SHA: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- execution grade remains not promoted.

Current unresolved buckets:

- 12,702 `TV_HISTORY_WINDOW_UNAVAILABLE`;
- 17,565 `TV_HLC_DISAGREEMENT`;
- 2,877 `TV_IDENTITY_OR_PROVIDER_ERROR`;
- 10,657 corporate-action residual rows.

This task targets ONLY the 2,877 TradingView identity/provider-error rows.

## Purpose

Determine whether the 2,877 identity/provider-error residual rows can be reduced through evidence-based ticker/provider identity remediation without weakening the existing price gate.

This is an AUDIT only. No Open value may be written into the derivative or immutable panel in this task.

## Frozen target

Load the exact row set classified as `TV_IDENTITY_OR_PROVIDER_ERROR` in the accepted targeted TradingView census artifacts.

Expected aggregate target count: 2,877 rows.

Known final TradingView error tickers from the accepted census are:

- `FREN`
- `MASA`
- `MFIN`
- `RMBA`
- `SMBR`
- `TURI`

Do not assume these six are semantically identical cases. Preserve the original HTTP/provider status and classify separately.

## Evidence-first identity workflow

Before any new network request:

1. inspect preserved TradingView request/error artifacts for each target ticker;
2. inspect existing project security master, listing intervals, ticker history / rename / relisting evidence, and corporate-action evidence;
3. inspect Yahoo/provider symbol history already preserved in the project;
4. produce a factual identity table with current ticker, historical ticker aliases if evidenced, listing dates, delisting/rename status, and source references;
5. do not invent or guess alternate tickers.

Only an alternate TradingView symbol/identity explicitly supported by project evidence may be tested.

## Network authorization

Network use is bounded.

- For `SMBR`, whose prior targeted census failure was HTTP 520, one retry of the unchanged canonical `IDX:SMBR` contract is authorized because the prior failure may be transient.
- For tickers with preserved 404/provider-not-found responses, do NOT repeat the same known-failing canonical request unless a materially different provider state is evidenced.
- Alternate symbol requests are allowed only when a documented historical/current alias relationship is established before the request.
- Keep `market=indonesia`, `resolution=1D`, `count=1000` unless the provider identity itself requires only the symbol string to change.
- Do not add pagination, date anchors, synthetic history, or alternate providers.

Preserve every new raw response and the identity evidence that justified the request.

## Admission gate

Any exact ticker/session row recovered through a remediated identity remains subject to the unchanged gate:

1. exact intended security/session identity;
2. exact certified panel High / Low / Close;
3. finite positive Open;
4. Open within certified Low--High;
5. row is not corporate-action residual.

No H/L/C mismatch row may be accepted merely because an alternate symbol returns an Open.

## Required metrics

Report at minimum:

- exact frozen target row count and SHA / source manifest;
- target rows and date range by ticker;
- preserved prior TradingView HTTP/provider status by ticker;
- identity evidence found for each ticker;
- aliases tested and justification source;
- network request / retry / 429 / error counts;
- exact ticker/date coverage obtained from remediation;
- exact certified H/L/C count;
- admissible Open candidates;
- unresolved rows after audit, by reason and ticker;
- immutable panel SHA before/after;
- derivative SHA before/after (must be unchanged);
- artifact hashes and manifest SHA.

## Hard boundaries

Do not:

- write Open candidates into any panel;
- alter the Yahoo + TradingView derivative;
- touch the 12,702 history-window bucket;
- arbitrate the 17,565 H/L/C-disagreement bucket;
- repair the 10,657 corporate-action bucket;
- use Investing, Yahoo refetch, Stockbit, or another provider;
- weaken exact H/L/C validation;
- start modelling, OHLCV alpha experiments, Ranking/PIT-sector work, execution PnL, paper/live trading, or broker integration.

Run focused tests and full pytest. Write a factual runtime checkpoint, push fast-forward, and STOP for independent ChatGPT review before any candidate application or wider provider work.

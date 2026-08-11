# Zapi TradingView Pro Resume — Runtime

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-tradingview-resume-v1`
Base: `288fc109bb042372885ee63be9c884eca9beceb5`
Decision: `STOP_FOR_INDEPENDENT_CHATGPT_REVIEW`

## Scope and controls

This runtime resumed only the unfinished TradingView set from the frozen
240-row sample. The 134 prior-success tickers were not refetched. FREN's prior
404/provider-error state was not retried because FREN was not in the exact
RATE_LIMITED set.

- Sample SHA-256:
  `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`
- Prior first-runtime candidate-row SHA-256:
  `5e9b7284629267ba0e04abfb02a95272cb0828c85b35354ff594b75962e78a10`
- Prior first-runtime row-audit SHA-256:
  `1e6583ae739c58a8b513fe93d564bdcfbf4bc31428733d293941f40d71ab6052`
- Prior first-runtime manifest SHA-256:
  `b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80`
- Prior follow-up manifest SHA-256:
  `87e40d23e02f7557d8a90120577ff68fd3e3567ee339c856386c141fdb61802d`
- Immutable panel SHA-256 before and after:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- Panel changed: `false`
- API key was visible only to the process and was never printed or persisted.

The TradingView request contract remained unchanged:
`symbol=IDX:<ticker>`, `market=indonesia`, `resolution=1D`, `count=1000`.
No Investing, `finance:idx/stock-history`, panel write, full-universe census,
corporate-action repair, modelling, execution-grade promotion, or execution
PnL was performed.

## Validation

- Focused tests: `7 passed`
- Full pytest before runtime: `258 passed, 5 warnings`
- The warnings are existing pandas FutureWarnings.

The first runtime process completed all 71 authorized network calls and wrote
raw evidence before encountering a local column-suffix bug while formatting
the arbitration metrics. The bug was fixed, focused/full tests rerun, and the
final summary was regenerated offline from the preserved raw evidence. No
network refetch occurred after that batch.

## Retry-set proof

- Frozen sample tickers: `206`
- Prior SUCCESS tickers: `134`
- Resume-selected tickers: `71`
- Selected ticker-list SHA-256:
  `bedc6324fcf716e4e4d5b1a214b3f88590557b76cd7d32e59d81eed29471cc25`
- Prior-success/resume set intersection: empty
- Prior successful tickers refetched: `0`
- FREN retried: `false`

## Incremental Pro resume

- Requests: `71`
- Retries: `0`
- HTTP 429: `0`
- Successful tickers: `67`
- Provider-error tickers: `4`
- Provider rows: `63,915`
- Exact sample-date coverage: `55 / 240`
- H/L/C exact: `33 / 240`
- Known-control H/L/C exact: `9 / 40`
- Known-control Open exact: `10 / 40`
- Missing-Open recovery candidates: `24`
- Recovery by role: `11 RESIDUAL_HLC_MISMATCH`, `13 RESIDUAL_PROVIDER_GAP`
- Recovery by year: `2021: 5`, `2022: 7`, `2023: 6`, `2024: 6`
- `HISTORY_WINDOW_UNAVAILABLE`: `17`
- Provider 404 errors: `MASA`, `MFIN`, `RMBA`, `TURI`

## Combined original + Pro resume

- Final ticker statuses: `201 SUCCESS`, `5 REQUEST_ERROR` out of `206`
- Final provider/symbol errors: `FREN` (preserved prior 404), `MASA`, `MFIN`,
  `RMBA`, `TURI` (resume 404s)
- Combined deduplicated provider rows: `193,959`
- Exact sample-date coverage: `156 / 240`
- H/L/C exact: `117 / 240`
- Known-control H/L/C exact: `32 / 40`
- Known-control Open exact: `33 / 40`
- `HISTORY_WINDOW_UNAVAILABLE`: `67`
- Missing-Open recovery candidates: `85 / 200`
- Recovery split: `35 RESIDUAL_HLC_MISMATCH`, `50 RESIDUAL_PROVIDER_GAP`
- Recovery by year: `2021: 15`, `2022: 25`, `2023: 26`, `2024: 19`
- Provider class counts: `TV_RECOVERY_CANDIDATE: 85`,
  `TV_HISTORY_WINDOW_UNAVAILABLE: 67`, `TV_HLC_DISAGREEMENT: 39`,
  `TV_IDENTITY_OR_PROVIDER_ERROR: 17`,
  `TV_PANEL_HLC_OPEN_EXACT_CONTROL: 32`

Yahoo mismatch arbitration across the combined 240 sample rows:

- Supports certified panel: `85`
- Supports certified panel and Yahoo: `32`
- Supports Yahoo: `7`
- Disagreement: `32`
- Unusable/no exact provider row: `84`

## Quota

Safe preflight quota headers before network calls:

- plan fingerprint: `PRO`
- monthly limit: `25000`, remaining: `24158`
- per-minute limit: `2000`, remaining: `2000`
- plan-expired marker: absent

The final successful TradingView response exposed:

- monthly limit: `25000`, remaining: `24062`
- per-minute limit: `2000`, remaining: `1963`
- plan-expired marker: absent

The separate post-run MCP metadata probe was connection-reset and is recorded
as unavailable; the final TradingView response headers are the after-quota
evidence. No key or response body was stored for the metadata probe.

## External artifacts

Runtime root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_tradingview_resume_v1_20260811`

The artifact manifest contains 9 files and was independently re-hashed with
all entries valid:

| Artifact | SHA-256 |
|---|---|
| `quota_after.json` | `af0647da0fe9c3ba29ccca9395e2d0be8da2d76f299d605e3aad138d42a2f825` |
| `quota_before.json` | `b9d3d9835095a6d8bfbe7e4b40005f829598323711badd3e618888171e7471e5` |
| `tradingview_combined_row_audit.csv` | `5922e397c85470456f927ea6339a8d4a1910160f65aaadccb55af9cef9f82712` |
| `tradingview_combined_rows_with_provenance.csv` | `d14795acfea27daed670150cb97a8647591439f4580c9c3ba98c5192f6b8306f` |
| `tradingview_combined_ticker_status.csv` | `d0528c270459d7fb47c77259745e5df2034d366eba95d7a07242e9ae545beb32` |
| `tradingview_resume_raw_responses.jsonl` | `b47dfd96d8088c69ca53fe5379029dd1b4ab01a05b9bc9c53adbbc0e6e2accf7` |
| `tradingview_resume_row_audit.csv` | `c14a93cf27aa6a3fa42defbe78cd83b347173fba51038006ed74515aa4bd4378` |
| `tradingview_resume_rows.csv` | `f9cc994c307ecc2fb892fba0a0c3d786a79aed681f748a64d96d9b8e59d83a74` |
| `tradingview_resume_ticker_status.csv` | `29514e9fef16cbacdb1d1066be854aa6ccbcf76bd333f97c1498279db6e9de3e` |

Artifact manifest SHA-256:
`68adea6bd6cf2b251b43e010133d8a3899c7d3ff8af8566f4bd9b88f0f9f3134`

Supplemental summary SHA-256:
`0424b2e5541cd3d30c116bc82af10189261400208e160413325b8b383aee38b0`

The combined result is preserved for independent review. It does not
authorize the targeted/full `49,476` residual census.

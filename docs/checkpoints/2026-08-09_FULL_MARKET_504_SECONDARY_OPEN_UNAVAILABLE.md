# 504-session repair checkpoint - secondary Open source unavailable

Date: 2026-08-09

Branch: `data/idx-data-002c`

## Decision

**504 FAILED - 1260 not started.**

The three historical price blockers were processed independently. No 252
diagnostic, 1260 expansion, modelling, `IDX-VAL-002`, or merge to `main` was
started.

## Validation

- Full pytest: **149 passed**, exit 0.
- Warnings: three existing non-blocking pandas `FutureWarning` messages.
- 504 window: `2024-06-21` through `2026-07-31`.

## Exact official fallback result

The missing ACTIVE date sets were regenerated from the repaired PIT identity,
official Stock Summary anchors, listing existence, and existing raw files:

| ticker | requested | PRICE_PARSED | FIRSTTRADE_FALLBACK | unresolved | filled | remaining |
|---|---:|---:|---:|---:|---:|---:|
| FREN | 196 | 0 | 0 | 196 | 0 | 196 |
| MASA | 22 | 0 | 0 | 22 | 0 | 22 |
| MFIN | 249 | 77 | 0 | 172 | 77 | 172 |

The official fallback used only positive Regular-Market Volume/Frequency,
positive valid High/Low/Close, positive OpenPrice when available, and positive
FirstTrade only as the documented fallback. No synthetic or forward-filled
price was created. Existing provider rows were not overwritten.

FREN and MASA had no accepted official opening rows. MFIN's 77 accepted rows
all used positive `OpenPrice`; the remaining 172 MFIN rows lacked a positive
official OpenPrice and FirstTrade. All unresolved official rows are retained
with diagnostic `OFFICIAL_OHLC_MISSING_OR_NONPOSITIVE`.

Runtime evidence is preserved in:

`D:\Documents\Project\idx-trade-data-gate-20260808v\repair_504_complete\`

## Secondary-open witness

The repository now contains a generic validator at
`src/idx_trade/secondary_open_witness.py` with regression coverage in
`tests/test_secondary_open_witness.py`.

It does not allow the secondary source to define session dates, identity,
ACTIVE state, High, Low, Close, or Volume. It requires exact ticker/date
matching, positive secondary OHLC, exact High/Low/Close equality with IDX, and
the secondary Open inside the official IDX Low/High range. Existing primary
rows are preserved.

Normal public requests to the candidate Investing.com historical pages returned
HTTP 403 for all three instruments:

- FREN: `https://id.investing.com/equities/smartfren-tele-historical-data`
- MASA: `https://www.investing.com/equities/multistrada-ar-historical-data`
- MFIN: `https://www.investing.com/equities/mandala-multif-historical-data`

The source was therefore recorded as unavailable. No anti-bot, CAPTCHA,
authentication, or rate-limit bypass was attempted, and no secondary Open was
accepted.

Automatic raw-price semantics are FREN=false, MASA=false, MFIN=true. MFIN's
77-row artifact is not sufficient because 172 ACTIVE sessions remain missing.

## Ladder and next phase

The 126/504 certification ladder was not run after this source-unavailable
stop. There is no new 504 panel or manifest. The previous failed gate and
repair artifacts remain preserved. Since genuine 504 PASS was not established,
the conditional 1260 phase is not authorized and was not started.

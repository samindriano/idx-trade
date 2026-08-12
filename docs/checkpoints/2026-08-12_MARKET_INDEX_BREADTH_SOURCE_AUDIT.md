# Market / Index / Breadth History V1 — bounded source audit

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/market-index-breadth-history-v1`
Base commit: `4efe5108398d772da5cb9711f7619e16bde853f4`

## Decision

`CONDITIONAL_SOURCE_READY_PIT_BLOCKED`

Official IDX and Zapi provide usable historical session-date context for index
summary and stock-summary rows. The source is not PIT-ready: neither the
official historical payload nor Zapi exposes first-publication time, revision
ID, or an immutable as-of snapshot. No defensibly complete PIT window is
certified in this checkpoint.

Breadth is also not source-ready as an official aggregate. The audited
endpoints expose per-security `Change`, not a published
advancing/declining/unchanged count. Derived change buckets are retained only
as an explicitly labelled audit result.

## Official endpoints and semantics

| Endpoint | Use | Semantics observed | Historical observation |
|---|---|---|---|
| `TradingSummary/GetIndexSummary` | rich index/session state | `COMPOSITE`/IHSG and other indices; Close, Previous, High, Low, Change, Volume, Value, Frequency, MarketCapital, NumberOfStock | 2020-01-02, 2021-01-04, 2024-06-21, 2026-07-30/31 returned rows |
| `TradingSummary/GetStockSummary` | per-security change/participation candidate | StockCode, Change, regular Volume/Value/Frequency, separate NonRegular fields, listed/tradable fields | 2020-01-02, 2021-01-04, 2024-06-21, 2026-07-31 returned rows |
| `DigitalStatistic/GetApiData` + `LINK_DAILY_TRADING_MARKET_REGNONREG` | market aggregate cross-check | regular/non-regular/total Value, Volume, Frequency; Value/Volume are million-scaled | Jan 2017 and 2024/2026 samples returned rows |
| `DigitalStatistic/GetApiData` + `LINK_DAILY_IDX_INDICES` | close-only index history | daily rounded close values, not rich OHLC/aggregate rows | Jan 2018 sample returned rows; Jan 2017 composite was absent in the tested sample |
| `Home/GetTradeSummary` | latest asset-class card | five current asset classes; no date parameter in frontend call | latest-only; not admitted as historical |

The direct official source returned no rows for Sunday 2026-07-26 and no rows
for the tested 2019-01-02 date, while 2020-01-02 returned 34 index rows. These
are bounded observations, not a claim of exhaustive calendar completeness.

## Zapi/direct parity

Representative direct IDX and Zapi raw payloads matched on all common rows and
all accepted fields:

| Dataset/date | Direct rows | Zapi rows | Accepted field exact-match |
|---|---:|---:|---:|
| Index / 2026-07-31 | 45 | 45 | 11/11 fields, 100% |
| Index / 2024-06-21 | 44 | 44 | 11/11 fields, 100% |
| Index / 2021-01-04 | 36 | 36 | 11/11 fields, 100% |
| Stock / 2026-07-31 | 963 | 963 | 15/15 fields, 100% |
| Stock / 2024-06-21 | 930 | 930 | 15/15 fields, 100% |
| Stock / 2021-01-04 | 717 | 717 | 15/15 fields, 100% |
| Latest `Home/GetTradeSummary` / 2026-08-11 | 5 | 5 | core fields, 100% |

`OpenPrice` was not part of the accepted contract or parity decision. It was
not used to construct market context.

Representative source-byte SHA-256 values (raw captures remain outside Git):

```text
Zapi index 2026-07-31: d76056c544ff3930cdd36b6824e3a30a3b542b4ae17a47838c03d7a525e3c624
Zapi index 2024-06-21: ff3139a0f85904ac8e6aa20d8638e6fa7169f3ef95969b7997eb7592811e3762
Zapi index 2021-01-04: e3ad38742c058ee80ea5eca60050c59514450a0029ac3792e198f2539e7579cb
Direct index 2026-07-31: 10725ef1e39228b51e36a3277a62e34cdb9c345664f82155bf989f626ed8ea3d
Direct index 2024-06-21: 1370917ef3e3f9abcefb087581bb5273ed1fc603ffc76d54bfcafa4829a87e39
Direct index 2021-01-04: 56d23ad60032545297aa3fd21a0d00e6963f8d5e7b5e4ae860ce2003a3f89487
Zapi stock 2026-07-31: d2280cbc629538fe13f3ebf9c191f351ca09d2e2cf475d2e3b803092e953571e
Zapi stock 2024-06-21: aca03d7e8dbf5d1e21db4e257502d1ed9fc9dc5829812af630c9fb9b9dfaa5cb
Zapi stock 2021-01-04: a0f307636ea065aa8f189e68c4f7fbb89ef5964d8abb79505e0bc937944dcab8
```

## Aggregate and breadth diagnostics

For 2026-07-31, rich `COMPOSITE` totals were:

```text
Volume 31,527,251,722 = regular 27,462,956,600 + non-regular 4,064,295,122
Value  IDR 18,244,914,440,556 = regular 12,987,074,064,000 + non-regular 5,257,840,376,556
Freq   1,938,839 = regular 1,938,040 + non-regular 799
```

The same reconciliation was exact for 2024-06-21. It was not exact for the
2021-01-04 sample: index minus stock-summary totals was volume `-15,329,700`,
value `-2,933,457,900`, and frequency `-1,840`. This historical mismatch is a
source-completeness/semantic blocker, not something to silently repair.

Derived stock-summary change buckets (positive regular volume only):

| Date | Rows | Positive-volume rows | Zero-volume rows | Advancing | Declining | Unchanged-traded |
|---|---:|---:|---:|---:|---:|---:|
| 2026-07-31 | 963 | 830 | 133 | 455 | 205 | 170 |
| 2024-06-21 | 930 | 825 | 105 | 372 | 205 | 248 |
| 2021-01-04 | 717 | 636 | 81 | 301 | 192 | 143 |

Zero-volume rows were excluded from unchanged. No official breadth field or
denominator (listed, tradeable, regular-active, security type, suspension
handling) was found, so these are not a canonical breadth series.

## Timing, revision, and invariant findings

* Historical `Date` is a session date, not first-publication time.
* Zapi `timestamp` is access/cache time; it cannot become `knowledge_at`.
* Two identical direct IDX calls for 2024-06-21 returned identical row bytes
  (`1370917ef3e3f9abcefb087581bb5273ed1fc603ffc76d54bfcafa4829a87e39`), and
  two Zapi calls returned identical cached bytes
  (`896fadec67ed7d1c600f207f0317a99eda810711a6ecd203f5a7ebe0c514eb28`).
  This demonstrates repeatability, not immutable revision history.
* Sampled aggregate fields were non-negative and index High/Low/Close
  invariants held. The stock summary exposes no listing date; lifecycle
  consistency cannot be proven from this endpoint alone.
* No open-price invariant was tested or used, per the separate OPEN source
  decision. Previous-price continuity requires adjacent sessions and was not
  promoted by this bounded sample.

## Final source decision

| Dimension | Decision |
|---|---|
| Official index discovery | `PASS` |
| Index units / rich fields | `PASS` for sampled IDX summary rows |
| Zapi access/parity | `PASS` for sampled rows; not canonical independent provenance |
| Historical session context | `CONDITIONAL_PASS` — available in tested 2020–2026 samples, not complete-window certified |
| Official breadth aggregate | `FAIL_CLOSED_NOT_FOUND` |
| PIT publication timing | `FAIL_CLOSED_UNRESOLVED` |
| Bulk historical PIT acquisition | `NO-GO` |

The strongest defensible statement is that official session-date market/index
context is discoverable and reproducible in the tested window, while no
defensible PIT historical window has been certified. A future forward EOD
capture or an official archive with publication/version metadata is required
before PIT use.

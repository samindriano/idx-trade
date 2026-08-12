# Market / Index / Breadth History V1 — source contract

Status: `CONDITIONAL_SOURCE_READY_PIT_BLOCKED`

This lane is a bounded source-foundation audit. It is not a modeling or
feature-engineering specification and does not authorize changes to the frozen
V3-B ranker or any outcome lane.

## Canonical candidate sources

The IDX frontend uses these official backend paths:

```text
GET https://block.idx.id/primary/TradingSummary/GetIndexSummary
GET https://block.idx.id/primary/TradingSummary/GetStockSummary
```

The frontend routes are the official Index Summary and Stock Summary pages.
The direct `block.idx.id` responses were reachable in this audit; the normal
`www.idx.co.id` host returned a runtime edge-protection response, so the
backend response was retained as the direct official payload rather than
replaced with another provider.

Zapi is an access/parity layer only:

```text
GET https://api.zpi.web.id/v1/finance:idx/index-summary
GET https://api.zpi.web.id/v1/finance:idx/raw
    ?path=TradingSummary%2FGetIndexSummary
    &query=...
```

The Zapi key was read only from `ZAPI_API_KEY`; it was not printed, stored, or
committed.

## V1 normalized contract

`canonicalize_idx_index_summary()` produces one row per
`session_date × index_code` with:

```text
session_date, index_code, previous, high, low, close, change,
volume, trading_value_idr, frequency, market_capital_idr, number_of_stock,
source, source_ref, source_url, source_sha256, source_retrieved_at,
knowledge_at, pit_timing_status
```

`canonicalize_idx_stock_summary()` produces one row per
`session_date × ticker` with regular-market quantities and the separately
reported non-regular quantities when present. It intentionally does not copy
or validate `OpenPrice`; OPEN remains a separate TradingView/source lane.

`derive_stock_summary_breadth()` is an audit-only transformation:

* `price_change > 0` and positive regular volume → advancing row;
* `price_change < 0` and positive regular volume → declining row;
* `price_change == 0` and positive regular volume → unchanged-traded row;
* zero regular-volume rows are reported separately and are not silently
  counted as unchanged.

The result is labelled
`DERIVED_STOCK_SUMMARY_CHANGE_BUCKETS_NOT_OFFICIAL_BREADTH`. No official
advancing/declining/unchanged aggregate or denominator rule was found, so this
derived result is not a canonical breadth feature.

`pit_timing_status` is fail-closed as
`UNRESOLVED_NO_PUBLICATION_TIMESTAMP`. The IDX historical payload contains a
session date, not first-publication time. The Zapi envelope timestamp is
provider access/cache time and cannot become `knowledge_at`.

## Digital Statistic findings

The official frontend also exposes:

```text
DigitalStatistic/GetApiData
  urlName=LINK_DAILY_IDX_INDICES
  urlName=LINK_DAILY_TRADING_MARKET_REGNONREG
```

The market-by-type response has `regularValue`, `regularVolume`,
`regularFreq`, separate non-regular fields, and total fields. Its value and
volume are represented in million IDR and million shares respectively; total
frequency is an integer count. A July 31, 2026 sample matched total volume and
frequency after scaling, but its total value differed from the rich
`TradingSummary/GetIndexSummary` response by IDR 3,286,207. This is therefore
an independent audit source, not an automatic replacement for the exact rich
summary.

The daily-index statistic is close-only and rounded (for example, July 31,
2026 IHSG was 6236.13 versus rich-summary close 6236.126). It is not used to
replace the rich index rows.

## Explicit exclusions

* No OpenPrice from IDX stock summary is accepted in this lane.
* `Value` is named trading value in IDR; “turnover” is not introduced as a
  separate ratio or semantic.
* No current/latest `Home/GetTradeSummary` response is treated as historical;
  the frontend call has no historical date parameter.
* No current-survivor reconstruction, model feature, realized outcome,
  protected-forward access, OPEN backfill, Path Risk, or PnL work is included.

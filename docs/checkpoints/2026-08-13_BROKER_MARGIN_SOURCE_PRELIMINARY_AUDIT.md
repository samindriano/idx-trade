# Broker / Margin Source Preliminary Audit

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/broker-margin-source-audit-v0`
Status: `PRELIMINARY_SOURCE_AUDIT_LIVE_PARITY_REQUIRED`

## Scope

Read-only source/semantics/PIT audit for the Zapi/IDX `broker-summary` and `margin-summary` lanes. No provider call using the user's API key, no bulk acquisition, no automation change, no feature/model work, and no forward-outcome access.

Repository searches before starting found no dedicated broker-summary or margin-summary branch/checkpoint/implementation. This is therefore not a rerun of an existing formal lane. The accepted `data/foreign-flow-v1` source audit remains the methodological comparison standard.

## Sources inspected

- Zapi IDX catalog and full endpoint reference: `https://zpi.web.id/api/finance/idx`
- Official IDX Broker Summary page: `https://www.idx.id/en/market-data/trading-summary/broker-summary`
- Official IDX Stock Summary page, which exposes `All Stock`, `Margin`, and `Short Selling` tabs: `https://www.idx.id/en/market-data/trading-summary/stock-summary`
- Official IDX Margin and Short Selling Stock List: `https://www.idx.id/en/market-data/stocks-data/margin-stock-list/`
- Official IDX trading-hours/mechanism page for margin/short-selling rules.

## Broker Summary — preliminary finding

Zapi documents `GET /v1/finance:idx/broker-summary` as a daily broker/exchange-member trading summary. The documented response is market-wide by broker and contains:

- `Date`
- `IDFirm`
- `FirmName`
- `Value`
- `Volume`
- `Frequency`
- `IDBrokerSummary`

The example has `recordsTotal=88` for 2026-06-12. The endpoint accepts a historical `date` parameter.

The official IDX website separately exposes a Broker Summary page with broker search, date selection, and download, supporting the claimed source family.

### Important semantic limitation

The documented Zapi response has no stock ticker and no buy/sell/net-side fields. Therefore this endpoint is **not per-stock broker flow** and cannot answer questions such as which broker accumulated or distributed a particular stock. It is aggregate exchange-member activity for the day.

Potential information is limited to market-level broker participation/concentration/regime statistics. Incremental value versus the project's existing market/index/activity context is therefore uncertain and likely modest.

### Unresolved before acceptance

- exact raw IDX endpoint/path and wrapper-to-direct parity;
- historical depth actually retrievable, not merely parameter support;
- whether Value/Volume/Frequency are one-sided, double-sided, or use another aggregation convention;
- completeness/pagination behavior across dates;
- non-session behavior;
- revision/byte stability of old dates;
- source publication time / first-knowable PIT timing.

Preliminary verdict: `SOURCE_FAMILY_REAL_SEMANTICS_LOW_GRANULARITY_LIVE_PARITY_REQUIRED`.

Do not automate or use as a model feature yet.

## Margin Summary — preliminary finding

Zapi documents `GET /v1/finance:idx/margin-summary` as `Ringkasan perdagangan efek margin` and explicitly warns that it is published **per margin period, not daily**; callers must inspect the returned date. Parameters are `date`, `length`, and `start`.

Documented per-stock fields are:

- `code`
- `low`
- `high`
- `close`
- `change`
- `value`
- `volume`
- `frequency`

The example for returned date 2026-07-14 reports `total=220` securities.

Official IDX Stock Summary exposes distinct `All Stock`, `Margin`, and `Short Selling` tabs. Official trading rules also require a specific margin sign on margin buy orders. This makes a margin-specific transaction-summary interpretation plausible.

### Critical semantic uncertainty

The current public documentation does not by itself prove whether the Margin tab/endpoint represents:

1. actual trades carrying the margin transaction sign; or
2. ordinary trading statistics for stocks that are merely margin-eligible.

The values in Zapi's example differ materially from the all-stock daily summary for the same stock/date, which is consistent with a transaction subset, but this is only an inference until direct raw/official field semantics are verified.

The separate official `Margin and Short Selling Stock List` is an eligibility list and must not be conflated with the transaction summary.

### Potential research value if subset semantics pass

If the values are actual margin-tagged trades, the endpoint can support per-stock leverage/crowding proxies when joined to total Stock Summary, e.g. margin-volume share, margin-value share, and margin-frequency share. These could be relevant later to fragility/path-risk/reliability research. No such features are authorized by this checkpoint.

### Unresolved before acceptance

- exact raw IDX endpoint/path and direct-source parity;
- exact meaning of the returned `date` and publication cadence;
- actual historical depth;
- whether rows represent margin-marked trades or merely margin-eligible securities;
- whether zero-activity eligible securities appear or only securities with margin activity;
- unit semantics for value/volume/frequency;
- relationship to same-date all-stock Stock Summary and to the official monthly margin-eligible list;
- pagination/completeness;
- revision stability;
- historical first-knowable/publication timing.

Preliminary verdict: `SOURCE_SEMANTICS_PROMISING_BUT_UNRESOLVED_LIVE_PARITY_AND_PIT_AUDIT_REQUIRED`.

Do not automate or use as a model feature yet.

## Relative priority

1. `margin-summary`: worth a bounded live source audit because it is per-stock and may expose genuinely new leverage/crowding information.
2. `broker-summary`: lower priority because the public contract is only aggregate per broker/day and contains no stock-side dimension.

## Next bounded gate

A separate local live audit may be authorized using the existing persistent `ZAPI_API_KEY`, modeled after `data/foreign-flow-v1`:

- resolve wrapper -> Zapi raw -> direct official IDX path;
- freeze 5–6 dates across multiple years/periods;
- compare complete row sets and fields exactly;
- test historical depth, exact returned dates, pagination, non-session behavior, and one repeated old-date capture for revision stability;
- for margin, reconcile each intersecting security against all-stock Stock Summary and the official margin-eligible list;
- record retrieval time only as an observation-time upper bound, never as historical `published_at` unless the source exposes publication evidence.

No bulk backfill or prospective automation should be authorized until that gate is reviewed.
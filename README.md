# IDX Trade Research

Personal research project for building a point-in-time, daily/EOD IDX trade-setup scoring and risk engine.

## Research scope (locked for V1 data foundation)

- Market: Indonesia Stock Exchange (IDX) equities.
- Timeframe: daily/EOD only.
- The research universe is point-in-time and dynamic; current survivors must never be backfilled into the past.
- Raw OHLC prices are execution prices and are never overwritten by adjusted prices.
- Missing price rows are not interpreted as suspensions.
- Listing state, tradability state, and provider-data availability are separate concepts.
- FCA/watchlist securities are excluded from the initial trade universe but may remain in the historical data store.
- Historical delisted securities remain in the historical universe before their effective delisting date.
- IPOs use an explicit warm-up state before becoming model-eligible.
- Model work must not begin until the data gate passes.

## Canonical state model

A security can have an existence state and a separate tradability state.

Existence:

- `NOT_LISTED`
- `LISTED`
- `DELISTED`

Tradability:

- `ACTIVE`
- `SUSPENDED`
- `FCA_WATCHLIST`
- `NO_TRADE`
- `UNKNOWN`

Data availability is separate again:

- `PRESENT`
- `DATA_MISSING`

A missing OHLCV bar is therefore never enough evidence to infer `SUSPENDED`.

## Price semantics

The codebase keeps distinct price layers:

1. `raw_*`: actual observed OHLC used for execution, gap, stop and target evaluation.
2. `total_return_adjusted_*` (optional): vendor-adjusted series such as Yahoo adjusted close. This is never used as an execution price.
3. Split-adjusted technical prices are intentionally **not** synthesized from `Adj Close`, because that factor may also include distributions/dividends. They must be built from explicit split events when the split-event history passes the data gate.

## Data gate

Before ML/model development, the data layer must demonstrate:

- listing interval correctness;
- suspension/resumption intervals when known;
- explicit unknown status when suspension history is incomplete;
- IPO warm-up behaviour;
- delisted history retained before delisting;
- no silent forward-filling across suspension/no-trade periods;
- corporate-action provenance;
- expected-vs-observed session coverage;
- internal gap detection;
- provider missing data distinguished from exchange trading state;
- reproducibility manifest for code, config, dependency environment and source snapshots.

## Migration policy

This repository selectively ports infrastructure ideas from `market-movement-analyzer`, but does **not** copy its anomaly objective, `BULLISH/BEARISH/NEUTRAL` labels, old financial backtest, old `confidence` semantics, or coverage logic.

The old repository remains a reference implementation only.

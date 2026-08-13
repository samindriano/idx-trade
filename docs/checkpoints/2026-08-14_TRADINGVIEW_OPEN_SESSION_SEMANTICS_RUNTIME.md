# TradingView Open / Session Semantics Forensic V1 — Runtime

Date: 2026-08-14
Branch: `data/tradingview-open-session-semantics-v1`
Runtime code commit before documentation: `ef7e152`

## Decision

`TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN`

The bounded probe establishes a session-boundary pattern: the regular IDX
request excludes observed pre-open bars, while the public extended request
includes them. It does **not** prove that those pre-open bars are opening-auction
executions. The pinned adapter/provider response contains no auction flag, trade
classification, or explicit auction-boundary field.

The frozen TradingView admission verdict remains unchanged:
`TRADINGVIEW_INTRADAY_ADMISSION_REJECTED`.

No panel write, model/feature work, Path Risk/O2 work, protected-outcome access,
timestamp shifting, OHLC repair, or Stockbit provenance substitution occurred.

## Lineage and immutable inputs

The existing admission artifact root was read-only:

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_admission_pilot_v1_20260814`

- admission artifact manifest SHA-256: `de7246e447a83b15c083d19a00808f13670d97f720bd1e28ce8756e02186e8ee`
- Mathieu normalized bars SHA-256: `332c26cb2a7951b2664d99349e4cfffeb516d5c416b0c37a5e6fe4bcdfff4f95`
- TV1D comparison SHA-256: `47c4cb5bd1d5f9fdf2138c39fefad9aa4b8277a7058d5e2d54f981d3d9aacdf9`
- daily comparison SHA-256: `e05c1b6a1bc7c6f31b3f58fe0e36828c61461f57a355ca3b969757c2cd83670f`
- request manifest SHA-256: `ca1271ab7551c2f4cdd3029b179a11748cb2a1892726477fa9b2e6b40603d4d8`
- canonical panel SHA before/after: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- pinned Mathieu upstream commit: `5baea86c8c7e576f13464919c86c3b4c4b0ecf4c`

Offline artifacts were written to a new external root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_open_session_semantics_v1_retry_20260814`

The first live attempt is preserved separately at
`...\\tradingview_open_session_semantics_v1_20260814`; it recorded a local
Node dependency wiring failure (`@mathieuc/tradingview` unavailable) for all
60 planned invocations and did not produce provider evidence. `npm ci` in the
adapter worktree repaired only that local environment issue. The successful
retry used the exact same frozen plan and a fresh artifact root.

## Offline forensic result

Stored raw metadata was inspected across 368 Mathieu responses:

- market info present: `368/368`
- timezone: `Asia/Bangkok` (UTC+7, offset-equivalent to WIB)
- regular session: `0900-1630`
- `subsession_id`: `regular`
- `has_extended_hours`: `true`
- public extended session: `0845-1630`
- private premarket metadata: `0845-0900`
- bar source/transform: `trade` / `none`
- no explicit auction/opening-auction field was present

Across 1,282 matched TV60 ticker-session groups:

- first admitted bar at 09:00 WIB: `1,183`
- first admitted bar later than 09:00: `99`
- first admitted bar before 09:00: `0`
- groups with a second bar: `1,227`
- bar-count distribution: `1:55`, `2:53`, `3:49`, `4:81`, `5:101`, `6:484`, `7:456`, `8:3`
- TV1D Open available on matched offline overlap: `292`
- TV60 vs TV1D Open mismatches: `122/292`
- TV60 vs TV1D Open exact: `170/292`
- first TV60 Open equal to canonical Open: `666/1,282`
- first TV60 Open equal to previous canonical close: `526/1,282`

The first/second-bar reconciliation was chronological by raw epoch. No raw
bar was shifted, substituted, repaired, or filtered to improve a metric.

## Bounded live probe

Frozen request matrix: 5 tickers (`BBCA`, `BBRI`, `BMRI`, `TLKM`, `ASII`) × 3
dates (`2021-07-01`, `2024-07-01`, `2026-07-01`) × 2 timeframes (`1m`, `5m`)
× 2 sessions (`regular`, `extended`) = `60` requests.

Contract: anonymous pinned Mathieu adapter, server `prodata`, symbol
`IDX:<ticker>`, adjustment `none`, no pagination/fetch-more, initial range
500, timeout 25 seconds.

- total requests: `60`
- `AVAILABLE`: `20`
- `UNCLASSIFIED_NO_DATA`: `40`
- provider/network errors: `0`
- 2021 status: `20 UNCLASSIFIED_NO_DATA`
- 2024 status: `20 UNCLASSIFIED_NO_DATA`
- 2026 status: `20 AVAILABLE`
- pre-open bars in regular responses: `0`
- pre-open bars in extended responses: `10`
- 2026 extended 1m first pre-open bar: `08:58 WIB` for all five tickers
- 2026 extended 5m first pre-open bar: `08:55 WIB` for all five tickers
- 2026 regular 1m/5m first bar: `09:00 WIB`

The 2021 and 2024 requests reached `connected + symbol_loaded` but timed out
without an update. They remain unresolved history/provider availability and
are not interpreted as proof of no data or proof of auction absence.

The 2026 paired result is therefore strong evidence that TradingView’s
`regular` session excludes bars before 09:00 while its public `extended`
session can expose them. It is not sufficient to label those bars as auction
executions, nor to explain the TV60 Open mismatch by auction semantics alone.

## External artifact hashes

Successful retry root contains 66 manifest entries, including 60 raw probe
responses. Hashes after the final offline verdict classification:

- `artifact_manifest.json`: `91e0d1de66a4be0f513f0b69c860b06f3b3d072b4d66ff6ac5eddf6c661bff01`
- `live/summary.json`: `a08392f1f6d3ed5e809c314f7f847b03493a2a2a5c1dbc16451fe1539f6f05e4`
- `live/probe_summary.csv`: `80eb1638d087c0633f59912e9658b55dac8e6ee985e76178baba57c104f3c33c`
- `offline/summary.json`: `4924224cf660bc61f8d70d0cbe5282611a2155fb647f7e9b76228a189ccb2b90`
- `offline/session_forensics.csv`: `36987ae1220b28afedfa463cef7ab2f48ffbceb6133d930051b70217f460e5b1`
- `offline/market_info_summary.csv`: `396a069664d8f13b5456ca382a2929b43caf04f0ba99acad8a413e27fd65a162`
- `pre_network_preparation.json`: `8a1a38df075c2b024297f9e5bcfb2c5fad39a1ebd89e8061f9f8ef104bd3c90b`

## Validation

- focused open/session tests: `6 passed`
- full pytest after implementation: `59 passed, 1 failed`
- unchanged pre-existing failure: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`; fixture emits two conflicts (`raw_close`, `vendor_adj_close`) while the assertion expects one
- `git diff --check`: passed
- canonical panel SHA after runtime: unchanged

# Foreign Flow Historical Acquisition V1 — Result

Date: 2026-08-14
Branch: `data/idx-foreign-flow-historical-acquisition-v1`
Parent: `data/idx-foreign-flow-forward-capture-v1@32bb1390303b9103ac53c6faa4d521c1352ee940`

## Decision

`CONDITIONAL_PASS_BOUNDED_OFFICIAL_IDX_HISTORICAL_EOD`

The official IDX `TradingSummary/GetStockSummary` endpoint delivered complete
retrospective EOD snapshots for every session in the frozen, previously
acquired official-session union from 2021-04-01 through 2026-08-13. This does
not establish a complete 2018-2020 session calendar, so the archive must not be
described as a complete 2018-2026 history.

Foreign flow from session `t` is usable only from the next official session
(`t+1`). `observed_available_at_utc` is the retrieval observation time, not a
retroactive publication timestamp.

## Historical-depth probe

The same official endpoint was probed at representative dates:

| Date | Result |
|---|---|
| 2018-01-02 | empty; rejected closed |
| 2018-06-01 | empty; rejected closed |
| 2018-12-28 | empty; rejected closed |
| 2019-01-02 | empty; rejected closed |
| 2019-06-03 | empty; rejected closed |
| 2019-12-30 | empty; rejected closed |
| 2020-01-02 | complete: 671/671 rows |
| 2022-01-03 | complete: 770/770 rows |
| 2024-01-02 | complete: 906/906 rows |
| 2026-01-02 | complete: 958/958 rows |
| 2026-08-12 | complete: 963/963 rows |

The 2020 positive probe proves endpoint depth at that date, but no complete
official 2020 session artifact was available locally and the current public
calendar retrieval did not establish the full 2020 calendar. Therefore 2020
was not silently included by weekday inference.

## Frozen session calendar

The acquisition used only the union of existing official IDX session artifacts,
with no calendar-day or weekday guessing:

- sessions: `1,288`;
- exact range: `2021-04-01` through `2026-08-13`;
- duplicate source-date overlaps: `89` (deduplicated by exact date);
- calendar CSV SHA-256: `2b597142190e7e7a3182b80c75dc3fec3e0bbbfe32948fb2d586b33b5844a536`;
- calendar source manifest: external `calendar/official_exchange_sessions.manifest.json`.

The underlying official-session sources are the already audited IDX Digital
Statistics / Daily Statistics artifacts. Public calendar retrieval for older
months was incomplete, so no older dates were inferred.

## Acquisition and coverage census

- source: official IDX `https://www.idx.id/primary/TradingSummary/GetStockSummary`;
- requested / complete / failed sessions: `1,288 / 1,288 / 0`;
- normalized rows: `1,129,024`;
- unique tickers across the archive: `983`;
- per-session rows: min `727`, median `904`, max `968`;
- zero-flow rows: `480,219` (`42.5340%`);
- malformed/rejected materialized rows: `0`;
- session errors: `0`;
- estimated HTTP requests: `1,290` (2 session-preparation requests plus 1
  Stock Summary request per session).

| Year | Sessions | Rows | Unique tickers | Row min / median / max | Zero-flow | Zero-flow rate |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 186 | 138,661 | 770 | 727 / 743 / 769 | 71,733 | 51.7326% |
| 2022 | 246 | 196,321 | 828 | 770 / 794 / 828 | 95,606 | 48.6988% |
| 2023 | 239 | 209,045 | 907 | 828 / 876 / 906 | 89,874 | 42.9927% |
| 2024 | 237 | 220,952 | 948 | 906 / 937 / 947 | 97,631 | 44.1865% |
| 2025 | 236 | 225,871 | 973 | 947 / 956 / 968 | 86,454 | 38.2758% |
| 2026 | 144 | 138,174 | 965 | 958 / 959 / 965 | 38,921 | 28.1681% |

Zero buy and zero sell are preserved as valid flow, not converted to missing.
The archive retains all official 4- and 5-character Stock Summary codes; no
common-share filtering was applied.

## Fail-closed and immutability checks

Every session stores, outside Git:

- exact raw response bytes;
- official endpoint and exact date parameter;
- retrieval start and observed availability UTC timestamps;
- `recordsTotal`, `recordsFiltered`, row count, completeness status;
- raw SHA-256;
- normalized Parquet and SHA-256;
- session manifest with provenance and causality contract.

The runner is resumable and exclusive: a valid artifact is never overwritten;
an existing different raw or normalized representation is a revision conflict.
The normalized contract rejects empty/partial responses, date mismatch,
duplicate/invalid tickers, missing/fractional/negative foreign counts, and
preserves `foreign_net = foreign_buy - foreign_sell`.

External archive root:
`D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1`

Archive manifest:
`archive_manifest.json`

Archive manifest SHA-256:
`fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`

## Scope boundary

No provider other than official IDX was used. No Financial PIT, Corporate
Actions, PIT sector, scheduler/ForwardEOD, O2, model, feature-performance,
protected outcome, or forward counter artifact was touched.

# Historical Calendar Provenance Recertification V1

Date: 2026-09-10 Asia/Jakarta  
Status: `HISTORICAL_CALENDAR_RECERTIFIED`

## Scope and boundary

This checkpoint recertifies only the two dates missing from the legacy source
report: `2021-04-29` and `2021-04-30`. It does not relabel the original
`official_exchange_sessions_1260.csv` as if its lost raw bytes or original
parser commit had been recovered.

No production, R2, Cloudflare, scheduler, provider, model, counter, or outcome
state was changed.

## Fresh official source evidence

The primary IDX Digital Statistics Daily Trading Table API was retrieved once
for April 2021 at 2026-09-10T00:48:26.7220665Z UTC; the response server date was
2026-09-10T00:48:28Z UTC and HTTP status was 200.

- source identity: `IDX_DIGITAL_STATISTICS_DAILY_TRADING_TABLE`
- raw body: `raw/monthly.json` in the external package
- raw body SHA-256: `5c050c0bbba08742699dd3bd4fb08512112ccd2be382a707498fc4ff25a3e1f3`
- parsed April sessions: 21
- parsed session-list SHA-256: `22a9f05cb019c6de454026194bfe0e838e7364a3a589eeb174954fa7947deb3e`
- independently recertified dates: `2021-04-29`, `2021-04-30`

The official Daily Statistics publication-listing endpoint was also attempted
(HTTP 200, body `[]`) and the official HTML page was retrieved (HTTP 200 but
client-rendered without date rows). Neither was substituted for the successful
primary API evidence.

## Producer identity

The original artifact-producing checkout remains unknown. Commit
`7f2f3781c3020d191794acb0067267cfba7f2634` introduced the persistence wrapper,
but the same-day producer/parser lineage continued through later API and
fallback changes.

The new package uses the current clean parser files from checkout
`d49b1540d4e6b29deddc0f47ca0cf7cacc9e3b75` (the checkout had an unrelated
notebook modification; the two parser files were clean):

- `src/idx_trade/session_backfill.py`: SHA-256
  `1c5415d19f9ea080ca9e41573d29271a3ae2a90c134da0f0290d7eed518e1423`, last
  touched by `c8c43ac66bd3215465978ac5f39d0b72feec8a3e`.
- `src/idx_trade/providers/idx_sessions.py`: SHA-256
  `e5dc31e7b4a96dce83187de34918cbe3a409294c56c5e6d07e107ee1f75b1535`, last
  touched by `0aac752bc1cb46ca3203e76751a9bd17eee8672a`.

## Immutable package and supersession

Final package:

`D:\Documents\Project\idx-trade-data-gate-20260910-historical-calendar-recertification-v2`

- provenance manifest SHA-256:
  `4178e1c3ff412d278ac1ad997c49868257a84d6b687364912d656e7cfa313666`
- package integrity manifest SHA-256:
  `ae6b1494df307c7b2c13eaded4d880d46022e8d989f135143e1463683f2f36cf`
- effective calendar SHA-256 (byte-identical to legacy calendar):
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- source coverage: legacy accepted `1258` plus new recertification `2` =
  `1260/1260`
- structural checks: sorted unique sessions, no duplicates, no extras, and
  weekday-only session semantics all pass.

The package explicitly supersedes the incomplete reconciliation manifest
`8af17028e44621f93311c9a238bdfcfbe8b92421f2bcd3f8a26a6310ac4db07` while
preserving the legacy calendar and source report as separate lineage layers.

## Offline acceptance

The prepared authoritative-calendar -> POST_EOD -> canonical Intraday reader
tests passed. The exact-main reader also accepted the real 2026-09-09 artifact:
963 records, manifest SHA-256
`ba795905e51ef4632cbc1dee0964dda642112cd348e94b13ef06a17309712b39`.


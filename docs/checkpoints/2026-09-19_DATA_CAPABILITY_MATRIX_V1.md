# Data Capability Matrix V1

Canonical detail: `2026-09-19_ALPHA_RESEARCH_PROGRAM_CHECKPOINT_V2.md`.

Full scoped inventory: `2026-09-19_ALPHA_DATA_INVENTORY_RESULT_V1.md`.

| Capability | Current status | Permitted use |
|---|---|---|
| Clean OHLCV identity/unique keys | `PASS` for inspected frozen artifact | structural diagnostics |
| Official session ordering | `PASS` frozen 1,260 dates | mask/calendar construction |
| Tradability anchors | `PASS` frozen artifact | same-session structural mask |
| Current-universe activity median metadata | `PARTIAL / METADATA_ONLY` (105/963 populated; no ticker-date PIT history) | inventory clue only; not an alpha input |
| Financial core-three finite support | partial: 70,520 rows | capability diagnostics |
| Financial all-five PIT/provenance support | partial: 34,412 rows; 30,994 after mask | C3 capability audit only |
| Population completeness | `UNKNOWN/BLOCKED` | no new-alpha claim |
| Historical-as-of authority | `UNKNOWN/BLOCKED` | no new-alpha claim |
| Corporate-action transition authority | `UNKNOWN/BLOCKED` | no target comparison |
| Revision/vintage completeness | `UNKNOWN/BLOCKED` | no target comparison |
| H5/H10 target authority | `BLOCKED` | protected |
| Same-window incumbent score | `UNKNOWN/BLOCKED` | no incremental comparison |
| Prospective outcome evidence | `BLOCKED` | separate protected process |

## Continuation source-capability additions — 2026-09-19

| Capability | Current status | Evidence / permitted use |
|---|---|---|
| Financial reporting age | `PARTIAL / NOT_ADMITTED` | `70,931` internally consistent age rows; coverage begins 2024; structural/source audit only, no public-availability or revision claim |
| Official execution/no-trade state | `PARTIAL / NOT_ADMITTED` | `1,104,064` rows over `1,260` sessions; exact source/cache/session reconciliation; semantics, completeness, PIT timing, vintage, and identity unresolved |
| Suspension/tradability intervals | `BLOCKED` | `76` intervals, `471` expanded duplicate key groups, only `1,168` regular overlaps; do not equate `NO_TRADE` with suspension or impute uncovered rows |
| Official IDX-IC sector archive | `PARTIAL / NOT_ADMITTED` | `22` structured 2022/2023 sheets, `1,607` current rows + `14` exit rows; document-level periods only, PDF-only gaps, `GWSA/KOTA` cross-sheet duplicates, no daily/PIT/identity/vintage authority |
| Unresolved CA price-scale residual | `BLOCKED` | `188` rows have `0/188` overlap with retained HLC overlay; one listing interval is only narrow evidence, not issuer/ISIN/event authority |

These additions do not widen admission. No row is promoted into a candidate or
protected evaluation packet without independent source-contract evidence.

## Continuation source-capability additions — 2026-09-20

| Capability | Current status | Evidence / permitted use |
|---|---|---|
| TradingView BBCA max history | `PARTIAL / SOURCE_BLOCKED` | 6,356 rows, 2000-05-31–2026-09-18; adjustment metadata present, but date/basis blocks differ from IDX and no PIT/revision/CA-event contract exists. Structural reconciliation only. |
| Investing BBCA max history | `PARTIAL / SOURCE_BLOCKED` | 2,065 rows, 2018-08-08–2026-09-18; 0 exact OHLCV matches on 1,568 IDX-overlap dates and variable scale. No historical basis/PIT contract. |
| Local BBCA cross-source price basis | `UNKNOWN / BLOCKED` | TradingView is 5x versus IDX through 2021-10-12 and 1x thereafter; Investing does not reduce to one scale. Do not rescale or admit. |

The local census also classifies current foreign-flow and stock-summary rows as
snapshot-only, active listings and investor-type HTML as metadata-only, and
Stockbit chart/stream surfaces as current or redacted metadata. No newly
audited surface is admissible.

## Panel-depth field-contract additions — 2026-09-20

| Capability | Current status | Evidence / permitted use |
|---|---|---|
| Historical panel-depth field semantics | `PASS_STRUCTURAL_ONLY / SOURCE_BLOCKED` | 19 fields, 18,835 rows, 12 symbols; structural arithmetic and quote ordering pass, but no field-level PIT, revision, identity, CA, or population-wide contract |
| Historical bid/offer quote state | `PARTIAL / SOURCE_BLOCKED` | Bid and offer are populated, with 18,604 both-positive rows; quote timestamp/age/depth/executable semantics and price units are absent. Future specification only |
| Historical foreign-flow shares | `PARTIAL / SOURCE_BLOCKED` | Buy/sell/net share arithmetic is exact on all rows; actor scope, aggregation, publication time, and revision/vintage are unresolved |
| Historical foreign-flow values | `UNKNOWN / SOURCE_BLOCKED` | Buy/sell/net value arithmetic is exact, but currency/monetary unit and PIT semantics are absent |
| Listed-share transition field | `PARTIAL / SOURCE_BLOCKED` | 23 adjacent transitions across 6 of 12 symbols; no event, effective date, issuer/ISIN, or CA/share-basis authority |
| Frequency field | `UNKNOWN / SOURCE_BLOCKED` | 13,371 distinct values and one zero; field definition and aggregation semantics are absent |

No row is promoted into a candidate or protected evaluation packet.

## Local surface census continuation — 2026-09-20

| Capability | Current status | Evidence / permitted use |
|---|---|---|
| Historical official foreign-flow archive | `PARTIAL / SOURCE_BLOCKED` | 1,288 sessions, 1,129,024 rows, 983 tickers; publication time, T→T+1 authority, identity/CA/revision and completeness unresolved |
| Listing/delisting lifecycle history | `PARTIAL / IDENTITY_BLOCKED` | 962 current rows and 163 delisting records / 159 tickers; six conflict tickers and 2,280 ambiguous issues; no daily PIT membership |
| Monthly LBRE free-float corpus | `PARTIAL / REMEDIATION_REQUIRED` | 25,262 canonical rows with 24,394 admitted and 868 unresolved; monthly issuer reports, not daily population-wide PIT history |
| Statutory free-float anchors | `PARTIAL / REMEDIATION_REQUIRED` | 2025-12-31 has 923 exact-share rows; 2026-03-31 is percentage-only; no continuous PIT/issuer/CA chain |
| HSC ownership event ledger | `PARTIAL / EVENT_ONLY` | 59 events, 55 active at cutoff; event-level only, not a daily ownership panel; completeness and revision unresolved |
| Broker/margin category snapshot | `SNAPSHOT_ONLY / BLOCKED` | One date, 220 margin rows and 965 stock rows; category semantics are not financing flow and no PIT/publication time exists |

None of these six surfaces is admitted for feature construction or candidate
evaluation.

## Historical foreign-flow source audit — 2026-09-20

| Capability | Current status | Evidence / permitted use |
|---|---|---|
| Historical official foreign-flow archive | `PASS_STRUCTURAL_ONLY / SOURCE_BLOCKED` | 1,129,024 rows, 1,288 exact official sessions, 983 tickers, all artifact hashes and net arithmetic exact; capability review only |
| Foreign-flow public availability | `UNKNOWN / BLOCKED` | Every session has `publication_time_known=false`; observed retrieval time and declared T+1 rule do not certify public availability |
| Foreign-flow identity/CA/revision | `UNKNOWN / BLOCKED` | Normalized ticker/date identity only; no issuer/ISIN transition, corporate-action, or revision/vintage fields |

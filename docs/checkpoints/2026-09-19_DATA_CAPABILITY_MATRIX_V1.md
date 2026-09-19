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

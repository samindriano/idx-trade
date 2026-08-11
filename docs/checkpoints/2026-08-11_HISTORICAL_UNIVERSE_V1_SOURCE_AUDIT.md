# Historical Universe V1 Source Audit

Date: 2026-08-11  
Branch: `data/historical-universe-v1`  
Scope: IDX listing lifecycle acquisition and survivorship audit only  
Verdict: **FAIL** for a promoted complete historical universe

## Execution boundary

The focused historical-universe tests passed before the audit.  No model,
feature, realized-outcome, Path Risk, OPEN-backfill, execution/PnL, PIT-sector,
or `main` work was performed.  The API key was read only from
`ZAPI_API_KEY`; it was not printed, persisted, or committed.

Final validation after the documentation update: focused suite `8 passed,
0 failed` in 2.17s; full suite `479 passed, 0 failed, 3 warnings` in 20.19s.
The three warnings are existing pandas `FutureWarning`s in
`curated_identity.py` and `tradability_anchor_reconstruction.py`.

## Endpoint inventory and semantics

| Layer | Endpoint | Observed fields / semantics | Coverage finding |
|---|---|---|---|
| Official IDX | `primary/StockData/GetSecuritiesStock` | `Code`, `Name`, `ListingDate`, `Shares`, `ListingBoard`; current securities snapshot | 962 rows, one `length=9999` page, current-only |
| Official IDX | `primary/DigitalStatistic/GetApiDataPaginated` with `urlName=LINK_DELISTING` | `code`, `issuerName`, `ListingDate`, `DeListingDate`; table labels are Listing Date and Delisting Date | 440 monthly requests, 1990-01 through 2026-08, 0 request errors |
| Zapi | `/v1/finance:idx/securities` | IDX current securities wrapper; `Code`, `Name`, `ListingDate`, `Shares`, `ListingBoard` | 962 rows; current-only |
| Zapi | `/v1/finance:idx/companies` | current issuer profile, status, listing date and company metadata | 962 rows; current-only, no lifecycle history |
| Zapi | `/v1/finance:idx/ipo` | `listingDate`, `listingType` (`baru`/`relisting`), code and name; year filter, max 200 rows | 2000/2005/2010 returned no records; 2015 returned 16 including one relisting (BUKK); 2020/2024/2025/2026 returned only `baru` records |
| Zapi | `/v1/finance:idx/market-activity?type=relisting` | current market-activity payload, no historical date/pagination controls exposed | 7 current activity rows; not a historical census |
| Zapi | `/v1/finance:idx/raw` | raw passthrough to `/primary/...`; preserves IDX payload fields | exact core-row cross-check for official delisting samples, but remains transport only |

The official `DeListingDate` field was mapped to the existing V1 inclusive
`listed_to` contract only as a candidate mapping.  The source label establishes
the delisting date, but does not by itself resolve relisting intervals when the
same ticker has reused or stale `ListingDate` values.  No date was invented.

## Acquisition result

- Official current snapshot: 962 rows / 962 unique four-character ticker codes.
- Official delisting history: 163 rows / 159 unique codes.
- Valid four-character evidence union: 1,109 ticker codes.
- Non-standard codes excluded from the four-character V1 canonicalizer:
  `MAMIP` (preferred stock) and `MYRXP` (Series B), both delisted on
  2025-07-18.  These are explicit scope exclusions, not silently repaired
  dates.
- Earliest observed delisting date: 1993-05-05.
- Latest observed delisting date: 2026-07-30.
- Observed listing-date range in delisting rows: 1979-05-22 through
  2018-10-05.

The source rows were mapped into the V1 candidate lifecycle columns with
source reference, URL, evidence level, and source-response SHA.  Strict
`canonicalize_lifecycle_records()` rejected the candidate table, as required.

## Explicit lifecycle blockers

| Ticker | Exact blocker |
|---|---|
| `BUKK` | two delisting rows share listed_from 1995-01-09 but end 2006-08-09 and 2009-12-01; current listing is 2015-06-29. Zapi confirms a 2015 relisting, but does not reconcile the two earlier records. |
| `SKBM` | two delisting rows share listed_from 1993-01-05 but end 1999-09-15 and 2009-12-01; current listing is 2012-09-28. |
| `INRU` | delisted 2002-03-20 while current snapshot still reports listed_from 1990-06-18, creating an open/closed overlap with no authoritative relisting start. |
| `ITMA` | delisted 2002-11-29 while current snapshot still reports listed_from 1990-12-10, creating an open/closed overlap with no authoritative relisting start. |
| `KIAS` | delisted 2004-09-29 while current snapshot still reports listed_from 1994-12-08, creating an open/closed overlap with no authoritative relisting start. |
| `UNTX` | one row has listed_from 1994-07-06 but listed_to 1994-04-27; later rows reuse the same listed_from through 1997-07-04 and 2015-12-07. |

These are source conflicts or missing relisting evidence, not parser errors.
They remain fail-closed and are not resolved by inferring a date from current
status or price presence.

## Zapi/direct IDX validation

The 962-code current snapshot from Zapi matched the official IDX snapshot.
`Name` and `ListingDate` matched exactly; `Shares` differed only in JSON
number representation (official float serialization versus Zapi integer
serialization, with equal numeric values).  Zapi raw passthrough matched the
official core delisting rows exactly for both 2000-01 (1 row) and 2025-07
(12 rows), including code, issuer, ListingDate, and DeListingDate.  This
validates Zapi as a useful collector/access layer, not as independent
historical authority.

## Current snapshot and price-panel audit

- Current official membership versus the evidence union at 2026-08-11:
  structural mismatch count 0 (all 962 current codes are present).
- Existing external raw-price panel: 922 parquet files, 450,893 rows,
  922 tickers, 2024-06-21 through 2026-07-31.
- Against the 962-ticker current official snapshot, that panel covers 921
  current tickers; 41 current tickers have no panel file and one panel ticker
  (`MFIN`) is historical/non-current.
- Price tickers with no lifecycle evidence: 0.
- Price rows affected by unresolved lifecycle conflicts: 2,280 rows across
  `BUKK`, `INRU`, `ITMA`, `KIAS`, and `SKBM`.
- `UNTX` has no price file in this panel.
- No clean outside-interval conclusion is promoted for the five conflicted
  tickers; their rows are quarantined as lifecycle-ambiguous rather than
  treated as valid coverage.

An independent older local panel was also located by the read-only audit:
932 tickers / 1,036,575 rows covering 2021-04-29 through 2026-07-31.  It has
36 current-snapshot tickers absent and six historical extras; this does not
repair the six official lifecycle conflicts and is not used to widen the
promoted window.

## Completeness decision

The strongest **candidate** operational period is the existing panel window
2024-06-21 through 2026-07-31, but it is not defensibly complete because five
price-bearing tickers have unresolved lifecycle conflicts.  No V1 complete
window is promoted.  The 1990-01 lower query boundary also is not treated as
proof that pre-1990 extinct securities are fully discoverable.

The next required source is an authoritative historical listing/relisting
archive or issuer/exchange evidence that provides the missing interval starts
and reconciles the duplicate delisting records.  Until then, the correct
state is `HISTORICAL_UNIVERSE_V1_FAIL_BLOCKED_LIFECYCLE_PROVENANCE`.

## External artifact hashes

Raw captures are intentionally outside Git.  SHA-256 values below identify
the exact audit inputs/outputs without committing runtime market data:

| Artifact | SHA-256 |
|---|---|
| official current response | `bbc7808d795cbd987757b171c3b33da07ce4f9bdbd71af9d0f07da9ae64655a5` |
| delisting month metadata | `93d525f2111fccac4009d2054f2059dac2f685d1e4910497fc05258b60aa58d0` |
| delisting candidate records | `7d1db5e2e73c9af9d2b26fe50c913a88efa1adfc326ced6f1c78827901e26c40` |
| price lifecycle audit summary | `4cfe1a41358be1cd78285efea125f9245d07a8d738b3658eab117eec4b3b5f8e` |
| Zapi/IDX cross-check summary | `4d3115a0b12baf6f553b8e9fb07a30a4387eaf2aaa32723cd5d89caab57e135a` |

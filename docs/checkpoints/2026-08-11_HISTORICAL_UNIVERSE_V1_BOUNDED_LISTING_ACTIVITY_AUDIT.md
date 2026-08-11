# Historical Universe V1 — Bounded Listing-Activity Audit

Date: 2026-08-11
Branch: `data/historical-universe-v1`
Scope: official IDX listing/relisting/delisting discovery and bounded-window
survivorship audit only
Verdict: **`FAIL_NO_COMPLETE_WINDOW`**

## Decision boundary

This checkpoint does **not** freeze Historical Universe V1 and does not claim
complete legal lifecycle reconstruction back to the first IDX listing. The
candidate research window `2024-06-21` through `2026-07-31` was investigated,
but it is not promoted because the official public relisting route provides no
completeness metadata and demonstrably misclassifies at least one known
relisting (BUKK appears in the IPO response but not the Relisting response).
Pre-window lifecycle conflicts therefore remain fail-closed and can still
invalidate a bounded survivorship claim.

No PIT-sector, OPEN/backfill, corporate-action, model, feature, outcome, Path
Risk, execution/PnL, or `main` work was performed.

## Official IDX frontend/API discovery

Official page:
`https://www.idx.id/id/perusahaan-tercatat/aktivitas-pencatatan`

The page exposes New Listing, Delisting, and Relisting tabs. Its route bundle
(`0edee8c.js`) identifies these data sources:

| UI tab | route in the official bundle | observed request contract |
|---|---|---|
| New Listing | `/primary/ListingActivity/GetIpoRelisting` | `status=ipo`, `year`, `indexFrom`, `pageSize`, `emitenType`, `language` |
| Relisting | `/primary/ListingActivity/GetIpoRelisting` | `status=relisting`, same parameters; known BUKK anomaly requires also auditing `RencanaStatus` in `status=ipo` |
| Delisting | `/primary/ListingActivity/GetDelisting` | route is present in the frontend, but direct GET and POST returned HTTP 404 during this audit |

The exact frontend-shaped official listing/relisting queries were:

`/primary/ListingActivity/GetIpoRelisting?status=ipo&year=YYYY&indexFrom=0&pageSize=9999&emitenType=*&language=en-us`

and

`/primary/ListingActivity/GetIpoRelisting?status=relisting&year=YYYY&indexFrom=0&pageSize=9999&emitenType=*&language=en-us`

The response contains `SearchCriteria` and `Result`. Important `Result` fields
are `KodeEmiten`, `NamaEmiten`, `RencanaStatus`, `TanggalPencatatan`,
`Delisting`, `PapanPencatatan`, `EfekType`, and the security-class flags.
`RencanaStatus` was observed as `baru` or `relisting`. With the exact
frontend-shaped parameters, `status=relisting` returns SKBM/TALF/INCF in its
respective years, but it omits the known 2015 BUKK row; BUKK appears only in
the same endpoint's `status=ipo` response with `RencanaStatus=relisting`.
Therefore the audit checks both official response modes, but does not treat
either mode as a complete historical relisting census.

The frontend's year selector exposed only the current year and four previous
years, but the endpoint accepted manually supplied years. The frontend loads
an oversized page and paginates locally. The API returns no separate total and
its offset behavior is page-like/non-obvious, so a single oversized page was
used for each year and the returned `SearchCriteria` and row count were
retained. This does not by itself prove archival completeness.

## Coverage acquisition

Annual official `GetIpoRelisting` responses were acquired for 1990–2026:

- 37 `status=ipo` requests, 0 request errors;
- 2013–2026 returned 506 rows;
- 1990–2012 returned zero rows, so no pre-2013 completeness claim is made;
- 505 rows had `RencanaStatus=baru`;
- 1 `status=ipo` row had `RencanaStatus=relisting` (`BUKK`, `2015-06-29`);
- exact `status=relisting` scan returned 3 rows: `SKBM` (2012-09-28),
  `TALF` (2014-01-17), and `INCF` (2016-09-06);
- inside the candidate window: 47 new listings, 0 relistings.

Candidate-window official delisting evidence remains the direct IDX
DigitalStatistic `LINK_DELISTING` monthly source because the ListingActivity
Delisting route returned 404:

- 440 monthly requests, 1990-01 through 2026-08, 0 request errors;
- 163 delisting rows / 159 codes overall;
- 16 delisting rows intersect the candidate window;
- 962 current official securities are available from
  `StockData/GetSecuritiesStock`;
- the bounded union is 978 observed codes, or 976 four-character V1-scope
  codes after explicit exclusion of `MAMIP` and `MYRXP`.

The four bounded entry/exit mechanisms are therefore covered as follows:

1. securities present at the left boundary and still current: official current
   snapshot, filtered to `listed_from <= 2026-07-31`;
2. new listings during the window: annual official listing/relisting endpoint;
3. relistings during the window: the same endpoint's `RencanaStatus=relisting`
   rows, with zero observed in the window;
4. delistings during the window: official monthly IDX delisting history.

The candidate-window entry/exit counts are useful diagnostics, but they do not
establish a complete bounded membership claim because the same known BUKK
relisting is omitted by the exact Relisting filter and appears only as a
different status in the IPO response.

## Six conflict tickers

| ticker | bounded-window result | remaining historical issue |
|---|---|---|
| `BUKK` | resolved for the window; official relisting `2015-06-29`, current at right boundary, no window exit | duplicate pre-2013 delisting rows remain unreconciled |
| `INRU` | bounded-window status resolved by current-right membership and no entry/exit event in the window | exact post-2002 relisting start is not recovered |
| `ITMA` | bounded-window status resolved by current-right membership and no entry/exit event in the window | exact post-2002 relisting start is not recovered |
| `KIAS` | bounded-window status resolved by current-right membership and no entry/exit event in the window | exact post-2004 relisting start is not recovered |
| `SKBM` | official Relisting response identifies `2012-09-28`; no entry/exit event in the window | duplicate pre-2013 exits remain unreconciled |
| `UNTX` | historical conflict has no candidate-window exposure; not current and no panel file; official 2015-12-07 exit is before the window | malformed/duplicate pre-window lifecycle rows remain quarantined |

No relisting date was inferred from price observations.

## Price-panel audit after bounded reconciliation

The existing panel remains 922 parquet files / 922 tickers / 450,893 rows for
`2024-06-21..2026-07-31`. It contains 2,280 rows across five conflict tickers
(`BUKK`, `INRU`, `ITMA`, `KIAS`, `SKBM`).

- strict full-lifecycle canonical audit: **2,280 rows remain quarantined** as
  lifecycle-conflict rows;
- bounded status diagnostic: **0 observed entry/exit rows fall inside the
  candidate window**, but this is not promoted to completeness because the
  relisting endpoint is not demonstrably exhaustive;
- `UNTX` contributes zero panel rows;
- no price row is promoted as evidence for a relisting date;
- this checkpoint does not turn the quarantined rows into globally canonical
  lifecycle intervals.

Thus the bounded result remains fail-closed: the strict lifecycle table is
non-canonical, and the public listing/relisting API does not prove that no
unseen relisting crosses the window boundary.

## Provenance hashes

Raw captures remain outside Git. The following hashes identify the inspected
inputs:

- official page HTML: `69803970743ab24b47f056c0411223f0e2dc5bef27dd2f778a788757578f95ef`;
- official route bundle `0edee8c.js`:
  `3a55132834e1b51b2e70bcff529e600a3e893384c907356d9d37130907c4550d`;
- official Nuxt runtime `a5dd43c.js`:
  `062e188b2639d2e586cc5d7dd44d7048e72b02b164aeeab71ec6f6fd673beb6b`;
- exact annual listing-activity capture summary:
  `eff42d3daab79c3ef515c628351eb5b03a3e8c8e91f751040b19e5570ab07b6c`;
- exact annual Relisting capture summary:
  `42cc661a64c451a9cee92c04240d377009a3bbf39b0a7b24d721008a36fb270b`;
- official current snapshot:
  `bbc7808d795cbd987757b171c3b33da07ce4f9bdbd71af9d0f07da9ae64655a5`;
- official delisting candidate records:
  `7d1db5e2e73c9af9d2b26fe50c913a88efa1adfc326ced6f1c78827901e26c40`;
- prior strict price-lifecycle summary:
  `4cfe1a41358be1cd78285efea125f9245d07a8d738b3658eab117eec4b3b5f8e`.

## Final bounded decision

`FAIL_NO_COMPLETE_WINDOW`.

`2024-06-21..2026-07-31` remains the strongest physically available candidate
window, but no complete bounded window is promoted. Historical Universe V1 is
not frozen, and any future use still requires authoritative relisting evidence
or an explicit archive-completeness contract.

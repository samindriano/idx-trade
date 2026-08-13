# IDX-BEI Issued History + Financial Report Bounded Discovery

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/idx-direct-endpoint-audit-v1`
IDX-BEI source: `nichsedge/idx-bei` at `75d6c0f74fa360d225794c70c383348977de6798`
Status: `PARTIAL_SOURCE_USEFUL_NOT_PIT_READY`

## Scope and controls

This was the final bounded discovery pass authorized after the documented
`IDXClient` transport had already been validated. The previously tested
`LINK_FINANCIAL_DATA_RATIO` PIT-sector path was not retested.

- Transport: `idx-bei` `IDXClient`, repository default `curl_cffi`
  `impersonate="chrome"`.
- Client controls: `max_retries=0`, `delay_seconds=0`, one request per probe.
- Corporate-action probes: eight `GetIssuedHistory` categories, with
  `dateFrom=""`, `dateTo=""`, `start=0`, `length=25`.
- Financial-report probes: six `GetFinancialReport` requests for BBCA, BMTR,
  and PALM, annual audit reports for 2022 and 2024.
- Total requests: 14; HTTP 200: 14; retries: 0; additional pagination: 0.
- No bulk backfill, dataset/model integration, protected outcome access,
  retraining, scoring, or IDX-Trade artifact mutation was performed.
- The earlier announcement provenance retry was not repeated after the known
  bounded HTTP 503 result.

Raw responses and per-request metadata remain outside Git:

`D:\Documents\Project\idx-direct-endpoint-audit-20260813\final_discovery_20260813`

The external manifest contains exact endpoint, parameters, UTC access time,
status, content type, response headers, raw-byte SHA-256, and parsed response
summary for every request.

Manifest SHA-256:

`9c1c73d95fc5951b0afc18493351577e9e35d321421ff8d675b0c6414428bf69`

## `ListingActivity/GetIssuedHistory`

Every returned row had the same six fields:
`id`, `KodeEmiten`, `TanggalPencatatan`, `JenisTindakan`, `JumlahSaham`, and
`JumlahSahamSetelahTindakan`. The endpoint returned `recordsTotal` and
`recordsFiltered`, allowing the bounded page to be distinguished from the
remote total.

| `caType` | `recordsTotal` | returned | unique tickers in page | returned `TanggalPencatatan` range | raw response SHA-256 |
|---|---:|---:|---:|---|---|
| `hmetd` | 241 | 25 | 25 | 2024-07-15 to 2026-08-03 | `eb6c4c3150276517249803ce5ad2f30e73df5152dc79c19c04d3c1fd22cd999f` |
| `PrivatePlacement` | 8 | 8 | 7 | 1989-09-20 to 2006-03-23 | `fffc43a3fae8a4c9838fe9553e6c74c7b7609a1dbf16db8382faece7d126bcd4` |
| `stockSplit` | 199 | 25 | 24 | 2023-12-12 to 2026-07-21 | `9921cf0e6f80b071cba89f8f5344ebd4d09bef46e34029e647a3552ecdc27213` |
| `reverseStock` | 5 | 5 | 5 | 2002-05-29 to 2005-03-28 | `96015c0f20c9bb34289ea3690595dd7063a55dce6755cb509c6b33ae5528b96d` |
| `BuybackSaham` | 1 | 1 | 1 | 2007-11-30 to 2007-11-30 | `66d71170bbffb09eb26d8f7866e2c689c8e9ead8f46b257bc8563cf36b2b718a` |
| `ipo` | 438 | 25 | 25 | 2025-01-09 to 2026-07-10 | `7e5d6b047dabc8e5727a4963b30bf764a1a17829fa14e1ab4570d130ee2ba481` |
| `companyListing` | 149 | 25 | 25 | 2001-07-18 to 2008-01-28 | `d1aefe09eb24820262336d1ee55be06e9f3b6b55fda21e364505e723125ff580` |
| `partialDelisting` | 35 | 25 | 25 | 2022-03-22 to 2026-05-04 | `01a70ffb5ca85ce7432fad11e3aa34a07401b516b75714d89b76f28aa679130f` |

### Interpretation

- The endpoint is useful for discovering corporate-action event candidates and
  share-count changes. `JumlahSaham` and
  `JumlahSahamSetelahTindakan` are directly available, and the requested
  action type matched `JenisTindakan` in every returned category.
- Some categories show deep historical records in the bounded response. The
  complete small categories reach 1989 (`PrivatePlacement`), 2002
  (`reverseStock`), and 2007 (`BuybackSaham`). For larger categories, the
  oldest date shown is only the oldest row in the first 25-row page; it is not
  a proven lower historical boundary.
- `TanggalPencatatan` is the only event-time field returned. It is a recording
  or listing-date field by name, not an explicit announcement timestamp or
  independently identified effective date. The response contains no
  publication date, announcement number, knowledge time, or attachment
  provenance.
- `recordsTotal > returned` for `hmetd`, `stockSplit`, `ipo`,
  `companyListing`, and `partialDelisting`. Therefore this bounded pass does
  not establish complete ticker coverage or a complete event history.
- A few rows contain zero share counts. Zero must remain an observed value and
  must not be silently converted into missing data. Any timeline would need
  category-complete reconciliation, date-semantics validation, and explicit
  handling of such rows.

### Shares-outstanding / corporate-action decision

`GetIssuedHistory` is **USEFUL_AS_OFFICIAL_EVENT_LEDGER_CANDIDATE**, but
`NOT_SUFFICIENT_AS_A_DEFENSIBLE_STANDALONE_SHARES_OUTSTANDING_TIMELINE`.
It can seed exact-ticker/date/action/share-count candidates. It cannot alone
prove the effective or publication date, completeness across all action types,
or a continuous shares-outstanding state.

## `ListedCompany/GetFinancialReport`

All six requests returned one report result and a non-empty attachment list.
The top-level result fields were `KodeEmiten`, `File_Modified`,
`Report_Period`, `Report_Year`, `NamaEmiten`, and `Attachments`. Attachment
records included `File_ID`, `File_Name`, `File_Modified`, `File_Path`,
`File_Size`, `File_Type`, `Report_Period`, `Report_Type`, and `Report_Year`.

| ticker/year | result count | report period | top-level `File_Modified` | attachments | non-zero file sizes | raw response SHA-256 |
|---|---:|---|---|---:|---:|---|
| BBCA / 2022 | 1 | Audit | 2023-01-26T18:34:38.897 | 7 | 6 | `8d2627b63064d321e73d151c1b93c97224b499054885374bc23fef91a59a74da` |
| BBCA / 2024 | 1 | Audit | 2025-01-23T17:30:34.603 | 11 | 6 | `9e49da0182279ea4b4d42148152c78b8e2adeb1c3da63203d5a88ef1c5497847` |
| BMTR / 2022 | 1 | Audit | 2023-03-24T16:50:09.213 | 8 | 7 | `6394d0e9b9fe33b27e59dbf48934240e9a6b80dc1f08511bf5966df1616e6e7d` |
| BMTR / 2024 | 1 | Audit | 2025-03-18T20:08:15.757 | 9 | 7 | `f9ed8edb41decaaf9f77d2750c97dd46d0f8eb2d6ba6195dc56cccf492383035` |
| PALM / 2022 | 1 | Audit | 2023-03-24T14:45:35.073 | 9 | 8 | `81fafb9dd4a51f75c83141120f5463742983c7a0d60743806a77a9b0dd68ebe7` |
| PALM / 2024 | 1 | Audit | 2025-03-27T15:46:17.207 | 13 | 9 | `967ffccc52898efbeabc9dfb5d9ccddd20899964055304092a42e27d52d12a0c` |

The attachments include official IDX portal paths for PDF, XLSX, and XBRL ZIP
files. Some announcement-linked attachments report `File_Size=0`, so the
metadata response is not proof that every linked file is currently retrievable.

### PIT publication-timing decision

`GetFinancialReport` is **POTENTIALLY_USEFUL_FOR_REPORT-DISCOVERY_AND_METADATA**.
It is **NOT_PIT_SAFE_AS_A_STANDALONE_PUBLICATION-TIMING_SOURCE** in this
probe. `File_Modified` is present and useful for provenance, but the payload
does not expose a separate `PublishDate`, announcement number, effective date,
or knowledge timestamp. It must be joined to an independently verified
announcement/publication record before a PIT availability date can be claimed.

## Data-family disposition

| Data family | Disposition for IDX-Trade |
|---|---|
| Issued/corporate-action history | Useful official candidate-event and share-count source; not standalone timeline-ready. |
| Financial-report metadata/attachments | Useful filing discovery and provenance source; publication timing requires announcement cross-check. |
| `LINK_FINANCIAL_DATA_RATIO` sector history | Dead end for PIT sector state; prior PALM cross-check remains negative and was not retested here. |
| `GetAllAnnouncement` in the earlier bounded PALM probe | Unresolved/blocked by HTTP 503; no additional retry was spent. |

## Final decision

The direct IDX transport can reach both requested endpoint families under the
documented client. The endpoint families are worth retaining as **bounded
discovery inputs**, but neither is promoted to a canonical PIT-ready source
from this pass. No dataset, model, scoring, protected outcome, or existing
IDX-Trade artifact was changed.

## Artifact inventory

The external `MANIFEST.json` records all 14 request metadata objects and raw
response hashes. Representative non-response artifact hashes are not used as
scientific evidence; the manifest hash above is the integrity anchor.

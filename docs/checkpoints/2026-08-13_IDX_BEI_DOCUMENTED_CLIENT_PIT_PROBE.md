# IDX-BEI Documented Client — PIT Sector Probe

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/idx-direct-endpoint-audit-v1`
IDX-BEI source: `nichsedge/idx-bei` at `75d6c0f74fa360d225794c70c383348977de6798`
Status: `TRANSPORT_WORKS_PIT_RATIO_NOT_SAFE`

## Method

The repository instructions were followed for a bounded test:

- base URL: `https://www.idx.co.id/primary`;
- `IDXClient` from `idx-bei`;
- repository default `curl_cffi` `impersonate="chrome"`;
- `max_retries=0` and `delay_seconds=0` for the bounded probes;
- no CLI `all`, historical backfill, pagination expansion, or dataset write.

The repository README explicitly describes this transport as browser
impersonation / Cloudflare bypass. It was used only because the user explicitly
requested testing the repository's documented usage. This is a transport fact,
not evidence that the endpoint is PIT-safe or approved as a canonical IDX-Trade
source.

The existing `idx-bei` tests remain green: `24 passed`. No source code was
changed in either repository.

## Access results

| Probe | Result |
|---|---|
| `/TradingSummary/GetStockSummary`, `date=20260811`, `start=0`, `length=5` | HTTP 200, `application/json`, 963 records in payload, 644,947 bytes |
| `/DigitalStatistic/GetApiDataPaginated` with `LINK_FINANCIAL_DATA_RATIO` | 15 bounded queries returned HTTP 200 JSON |
| `/NewsAnnouncement/GetAllAnnouncement` for PALM, 2023-09-01 to 2023-10-31 | HTTP 503 Cloudflare HTML; no announcement JSON recovered |

The initial direct non-impersonated probe remains separately recorded as HTTP
403. The 200 result therefore depends on the repository's documented Chrome
impersonation transport.

## Ratio endpoint contract and semantics

The bounded ratio queries used exact endpoint/parameters recorded in the
external raw artifacts. Returned records contain:

`code`, `stockName`, `sector`, `sectorCode`, `subSector`, `subSectorCode`,
`industry`, `industryCode`, `subIndustry`, `subIndustryCode`, `fsDate`,
`fiscalYearEnd`, financial metrics, and audit/opinion fields.

There was no publication/knowledge timestamp in the returned ratio rows. The
observed `periodQuarter` parameter must not be treated as a self-describing
calendar quarter. For BIPI with `periodYear=2022` and `type=quarterly`:

| `periodQuarter` parameter | returned `fsDate` |
|---:|---|
| 1 | 2021-09-30 |
| 2 | 2022-03-31 |
| 3 | 2022-06-30 |
| 4 | 2022-09-30 |

The effective report date must therefore be read from `fsDate` and independently
validated; the query parameter alone is not sufficient temporal evidence.

## PIT cross-check

The following classification observations were recovered from the ratio rows:

- BIPI: 2021-09-30, 2022-03-31, 2022-06-30, and 2023-09-30 all reported
  `Energy / Oil, Gas & Coal / Coal / Coal Distribution`.
- BMTR: 2022-09-30, 2023-03-31, and 2023-09-30 all reported
  `Consumer Cyclicals / Media & Entertainment / Media / Advertising`.
- PALM: both `fsDate=2023-06-30` and `fsDate=2023-09-30` reported
  `Financials / Holding & Investment Companies / Investment Companies`.

The existing PIT-sector evidence records PALM's official classification change
as effective `2023-10-02`. Therefore the ratio endpoint's sector hierarchy is
current/terminal or otherwise not a historical effective-state snapshot.

## PIT decision

| Use | Decision | Reason |
|---|---|---|
| `LINK_FINANCIAL_DATA_RATIO` sector fields as PIT history | `NO` | Pre-effective PALM row already carries the post-change Financials classification; no publication/knowledge date is returned. |
| `LINK_FINANCIAL_DATA_RATIO` financial report metadata | `POTENTIALLY USEFUL` | `fsDate` and financial-report fields are present, but publication timing and historical classification semantics require separate provenance. |
| `GetAllAnnouncement` through this client | `POTENTIALLY PIT-SAFE, UNVERIFIED` | It is the right kind of endpoint for publication/attachment provenance, but the bounded PALM query returned HTTP 503 HTML and no JSON. |
| `idx-bei` as a PIT-sector integration | `NOT READY` | It is a generic scraper/client, not a PIT event reconstruction layer; canonical IDX announcements, effective dates, knowledge times, and hashes still need the existing IDX-Trade provenance contract. |

This result does not alter the existing PIT inventory. Dedicated 2022/2023
classification references remain unresolved, and the 2026 effective date remains
unresolved.

## External artifacts

Raw responses and metadata remain outside Git:

`D:\Documents\Project\idx-direct-endpoint-audit-20260813\followup_pit_20260813`

The follow-up root contains 11 initial ratio responses, 4 quarter-semantics
responses, announcement failure metadata/raw response, summary metadata, and a
manifest. Manifest SHA-256:

`0c213a8fe035526a914ce5b4119730d8a60de4215202a99319db6355a6ef9e17`

Representative raw response hashes:

- BIPI 2021 query: `f2f770c965f45b37e9477070869eccf0ac34bb80c6b4a3f0b0f7e2fbf4ef49e9`
- PALM 2023 Q3 query: `a5ff09e02915f0ae604e3d37130a160a30d86752f66a7cedde43a46363aff961`
- BIPI quarter-parameter map Q4: `618619ffa8c3c27f0a8add6c2926a0c63b4bbdf127be2eddbd2cacb176ec6ce6`
- PALM announcement 503 response: `497003f68cc69167876522035a58b5eb6a3f970cd33be3c74feba479a07e043c`

## Boundary

No model integration, PIT artifact creation, data-gate change, bulk backfill,
protected outcome access, retraining, or rescore was performed.

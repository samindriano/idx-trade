# Official IDXData3 Stock_First_Trx audit - STOP

Date: 2026-08-09

Branch at audit start: `data/idx-data-002c`

Source head at audit start: `ffca7c51312ef96ce786913541c36a55edd4588c`

## Decision

**504 remains NO-GO / STOP.** The target SO archive family had zero usable
coverage for the remaining historical ACTIVE-price rows. No production SO
parser was implemented and no 504/126 ladder, 252 diagnostic, or 1260 run was
started.

## Exact target set

The post-official-fallback requirement was regenerated into a fresh external
audit workspace:

| ticker | required missing ACTIVE sessions |
|---|---:|
| FREN | 196 |
| MASA | 22 |
| MFIN | 172 |
| **total rows** | **390** |

The rows span 233 unique official-session dates from `2024-06-21` through
`2025-09-19`.

## Official SO availability

Official specification: `https://www.idxdata3.co.id/IDX%20Reporting%20PSPP/Revitalisasi/Specification%20Document-Report%20Revitalization_PUBLIK%20v1.0.pdf`

Official directory: `https://idxdata3.co.id/Download_Data/Daily/Stock_First_Trx/`

Normal public retrieval was attempted for every unique target date using
`SO[YYMMDD].zip`. The expected `www` hostname failed TLS hostname
verification. The official canonical hostname was also tested without
disabling certificate verification or bypassing access controls. The initial
canonical pass returned 12 HTTP 404 and 221 HTTP 503 responses. One controlled
retry returned HTTP 404 for all 221. Final direct-file result:

- files available: 0/233 (0.0%);
- files unavailable: 233/233 `FILE_NOT_FOUND`;
- first available target date: none;
- last available target date: none.

The readable official directory advertised 133 SO files from
`SO200203.zip` through `SO200819.zip`, an observed public listing range of
2020-02-03 through 2020-08-19. No target date was advertised.

## Schema sample

The available `SO200819.zip` sample was saved only in the external audit
workspace. It contains one legacy fixed-width DBF member with 657 rows and
fields:

`STK_CDAT`, `STK_CODE`, `STK_NAME`, `STK_FIRST`.

It is outside the target window and does not expose the modern H/L/C,
Regular-Market volume, or frequency fields required for the requested
cross-check. No production parser was added.

## Per-ticker result

| ticker | SO files available | ticker rows found | official Open verified | unresolved | reason |
|---|---:|---:|---:|---:|---|
| FREN | 0 | 0 | 0 | 196 | `SO_FILE_MISSING` |
| MASA | 0 | 0 | 0 | 22 | `SO_FILE_MISSING` |
| MFIN | 0 | 0 | 0 | 172 | `SO_FILE_MISSING` |

No H/L/C cross-check was possible because no target archive existed. Yahoo,
Stock Summary, and certified 43/126 artifacts were not overwritten.

The exact availability CSV, per-ticker resolution, directory listing, and
schema evidence are retained externally and intentionally excluded from Git.

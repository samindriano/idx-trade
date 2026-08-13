# Financial PIT Direct IDX Publication-Chain Audit — 2026-08-13

Status: bounded direct-source audit complete; no bulk acquisition authorized.

Branch: `data/financial-pit-v1`

## Decision

Final verdict: `PARTIAL_SOURCE_USEFUL_PIT_COVERAGE_INCOMPLETE`

The direct IDX chain is usable for bounded filing discovery and publication
linkage when the issuer announcement is still exposed. It is not promoted to
complete Financial PIT acquisition because the public announcement history is
retention-limited, the endpoint does not expose a demonstrated immutable
restatement/version chain, and pagination behaviour is not safe to assume from
`recordsTotal` alone.

No financial features, model work, protected outcomes, or bulk acquisition were
performed.

## Scope and transport

The audit reused `nichsedge/idx-bei` at
`D:\Documents\Project\idx-bei-direct-audit-20260813`, using its documented
`idx.core.client.IDXClient` and repository-default `curl_cffi` transport with
`impersonate="chrome"`.

Controls:

- `max_retries=0` and `delay_seconds=0` for bounded probes;
- direct base URL `https://www.idx.co.id/primary`;
- no Zapi calls and no provider fallback;
- raw API responses and attachments remain outside Git;
- capture manifest: `D:\Documents\Project\idx-trade-financial-pit-direct-audit-20260813-v6\MANIFEST.json`;
- manifest SHA-256: `a60f7af03e42b4c02c8dcafa5eec7064b3bb16ff3fe3b826cf9976f6b699a898`;
- 12 logical records and 37 raw files; capture timestamp in the manifest is
  `2026-08-13T09:30:47.804028Z`.

## Endpoint contracts observed

### `ListedCompany/GetFinancialReport`

Exact bounded request shape:

```text
periode=audit|tw1|tw3
year=YYYY
indexFrom=0
pageSize=100
reportType=rdf
kodeEmiten=TICKER
```

Response schema observed:

- top level: `Search`, `ResultCount`, `Results`;
- result fields: `KodeEmiten`, `File_Modified`, `Report_Period`,
  `Report_Year`, `NamaEmiten`, `Attachments`;
- attachment fields: `Emiten_Code`, `File_ID`, `File_Modified`, `File_Name`,
  `File_Path`, `File_Size`, `File_Type`, `Report_Period`, `Report_Type`,
  `Report_Year`, `NamaEmiten`.

The response exposes period/year and file metadata, but no publication timezone,
announcement reference, knowledge timestamp, or statement-scope field. Scope
must remain explicit from a separately parsed statement artifact; it must not be
inferred from a filename or endpoint parameter.

### `ListedCompany/GetAnnouncement`

Exact bounded request shape for each filing-month join:

```text
kodeEmiten=TICKER
emitenType=*
indexFrom=0
pageSize=100
dateFrom=YYYYMM01
dateTo=YYYYMMDD
lang=id
keyword=
```

Response schema observed:

- top level: `ResultCount`, `SearchParams`, `Replies`;
- announcement fields: `Id2`, `NoPengumuman`, `TglPengumuman`,
  `JudulPengumuman`, `CreatedDate`, `Kode_Emiten`, plus issuer flags;
- attachment fields: `PDFFilename`, `FullSavePath`, `IsAttachment`,
  `OriginalFilename`, `JMSXGroupID`, `CorrelationID`.

The deterministic join key used here was the exact report `File_Name` matched
against announcement attachment `OriginalFilename`, `PDFFilename`, or the
basename of `FullSavePath`. The join was not inferred from title or date alone.

## Primary direct-IDX samples

All primary API requests returned HTTP 200. Attachment URLs were fetched
directly from the official `www.idx.co.id` URLs returned by the two endpoints.
`report_file_sha256` and `announcement_file_sha256` are equal in every row.

| Filing | Report period/year | Report `File_Modified` | Selected attachment / type | Report file SHA-256 | Announcement ref / `TglPengumuman` | `CreatedDate` | Announcement file SHA-256 | Join |
|---|---|---|---|---|---|---|---|---|
| BBCA FY 2024 | Audit / 2024 | `2025-01-23T17:30:34.603` | `FinancialStatement-2024-Tahunan-BBCA.xlsx` / XLSX | `0fb2f5ae05e4a9b90f593500ad251260d21d2e4cf0d2b5e4280da2d335d05126` | `003/ACT/2025` / `2025-01-23T17:30:34` | `2025-01-23T17:39:05` | same | PASS |
| BBCA Q1 2025 | TW1 / 2025 | `2025-04-23T17:28:34.323` | `FinancialStatement-2025-I-BBCA.xlsx` / XLSX | `6500e5683e981aee063bb5ae752bb147725f8d1a2148a09c9e698691381922bb` | `008/ACT/2025` / `2025-04-23T17:28:34` | `2025-04-23T17:37:04` | same | PASS |
| AADI FY 2024 | Audit / 2024 | `2025-03-04T18:44:28.883` | `FinancialStatement-2024-Tahunan-AADI.pdf` / PDF | `f92bf5e05542e845419883cfc105cf95431dfcb885ddbc31739aa2e9dd327aa8` | `AAI/009/III-25/corsec` / `2025-03-04T18:44:28` | `2025-03-04T18:58:06` | same | PASS |
| AADI FY 2024 | Audit / 2024 | same | `FinancialStatement-2024-Tahunan-AADI.xlsx` / XLSX | `b6ff2117193410503510c154190f02e5530fb8cc7524368a09ba811b58bd5642` | same announcement | same | same | PASS |
| TLKM 9M 2025 | TW3 / 2025 | `2025-10-30T20:20:21.537` | `inlineXBRL.zip` / XBRL ZIP | `85d8230c21f429d75e667ccc007914dc31f2d465ad1e369a5ae2249a57fec986` | `Tel.36/LP 000/COP-M0000000/2025` / `2025-10-30T20:20:21` | `2026-02-20T14:31:04` | same | PASS |
| TLKM 9M 2025 | TW3 / 2025 | same | `FinancialStatement-2025-III-TLKM.xlsx` / XLSX | `65ffef8eecf97b2e5bddca5a3047d1e62308be1244525c48b92d9958aad03ff3` | same announcement | same | same | PASS |

The report `File_Path` and announcement `FullSavePath` were both retained in
the external manifest. Representative announcement attachment paths include:

- BBCA FY2024: `.../20250123173557-49562-0/FinancialStatement-2024-Tahunan-BBCA.xlsx`;
- BBCA Q1 2025: `.../20250423173435-52112-0/FinancialStatement-2025-I-BBCA.xlsx`;
- AADI FY2024: `.../20250304185400-49874-0/FinancialStatement-2024-Tahunan-AADI.pdf`;
- TLKM 9M 2025: `.../20260220141849-57687-0/inlineXBRL.zip`.

Each was HTTP 200, non-empty, and had a matching content type (`XLSX`, PDF,
or `application/x-zip-compressed`). The four previously preserved official
XLSX hashes also match exactly: BBCA FY2024, BBCA Q1 2025, AADI FY2024, and
TLKM 9M 2025 are all 4/4 direct-byte matches.

## Request-level provenance

The detailed request parameters and raw hashes are in the external manifest.
The primary sample raw API hashes are:

| Filing | Financial-report JSON SHA-256 | Issuer-announcement JSON SHA-256 | Result count / returned replies |
|---|---|---|---:|
| BBCA FY 2024 | `e0df7631c3ceb125bb46dfd1f0ee64a476d7bfc65e92fd75024cdcd86797eae8` | `2ec783b3f0a2a7955ed3aa698a4d7431fc3a03b6f5d133a3bb0f875ec860a2e3` | 1 / 6 |
| BBCA Q1 2025 | `f18b9645abe5289d912273f162ed5b58fbee951aa91b55e95f9a11b1925fdb82` | `51d861a28e970794ee7b91b821c46b12ae0aafabbb9910041a0727afdeadc731` | 1 / 4 |
| AADI FY 2024 | `8a4ac3b0c602902e242b582363a4e5219eb6107ae31f2ce957f0db1c2552945e` | `02b93d60602a3c8a1e3b59a1d6fe75e16bd67e1a1531e8eb19c1002c4215eac0` | 1 / 5 |
| TLKM 9M 2025 | `5bdf92eb4d8f7fc4396b888e763d42745475e651d5eca6889a7f9a0e6646cccb` | `e4ba4610cc75b4fd2b39a9b8557e0c655e75a5186bc48c6b70c5f454359f5d43` | 1 / 6 |

The issuer-announcement `ResultCount` values are the total issuer records in
each month; all returned rows were present in the bounded page. The detailed
report/announcement path, exact params, statuses, content types, timestamps,
and raw file paths are in the external manifest rather than committed raw data.

## Time and publication semantics

- `File_Modified` equals `TglPengumuman` to the available second precision in
  all six primary report-file variants.
- `CreatedDate` is not a safe publication substitute. TLKM's announcement was
  published at `2025-10-30T20:20:21` but has `CreatedDate`
  `2026-02-20T14:31:04`, demonstrating later indexing/reprocessing metadata.
- IDX returns these timestamps without an explicit timezone field. The safe
  ingestion rule remains: interpret the naive issuer timestamps as
  `Asia/Jakarta`, then convert to UTC-aware values before applying the Financial
  PIT contract. Never use fiscal period end, filename date, workbook board date,
  or `CreatedDate` as publication time.
- The endpoint response does not expose statement scope. Consolidated/separate
  scope must be extracted and validated from the actual filing content before a
  filing enters a PIT fact table.

## Historical retention probes

| Filing probe | Financial report | Report attachment | Announcement query result | Publication join |
|---|---:|---:|---:|---|
| BBCA FY 2022 | 200; Audit/2022; XLSX SHA `182990a4e22eebe85907c31fcf6d7d9cc9229d75bad408ec8af7acacfe295a8c` | 200 | `ResultCount=0` for Jan 2023 | NOT FOUND |
| BBCA Q1 2023 | 200; TW1/2023; XLSX SHA `689e921cc0b5de6d1d6573d8561b7c0e6a95cde9e5169da902b1c8136fa781c9` | 200 | `ResultCount=0` for Apr 2023 | NOT FOUND |
| BBCA FY 2023 | 200; Audit/2023; XLSX SHA `10f4bd43ac38eb2b8270c2e68708dfd5b155adaf0efa4a28f2940d39c1df3c94` | 200 | `ResultCount=9` for Jan 2024 | `003/ACT/2024`, `2024-01-25T17:15:26`, file hash matches |

The direct report inventory remains available for old periods while the issuer
announcement publication record is absent for FY2022 and Q1 2023. This is
exactly the unsafe split between “file discoverable” and “publication time
proven.” It is not evidence that the old reports were never published.

## Pagination and revision observations

A bounded BBCA announcement query from `20240101` through `20260813` returned
HTTP 200 with `ResultCount=197`:

- `pageSize=100,indexFrom=0`: 100 replies;
- `pageSize=100,indexFrom=100`: 0 replies despite the same `ResultCount`;
- `pageSize=1000,indexFrom=0`: 197 replies.

This demonstrates that `ResultCount` cannot by itself certify a page is complete;
the adapter must validate returned rows against the declared total and use a
known-good pagination mode or fail closed. The 197-row bounded response exposed
11 BBCA financial-statement announcement records from FY2023 through FY2026,
one per observed reporting period and no duplicate same-period filename/ref in
this sample. That is not a demonstrated immutable revision chain: the financial
report endpoint returns one current row per issuer/period and the audit found no
separate restatement-version field or preserved version list.

Therefore corrections/restatements remain a high-risk unresolved contract. A
future adapter must preserve every captured report/announcement/attachment
version and reject same-key conflicting bytes; it must not overwrite an older
filing merely because the current endpoint returns a newer row.

## Gate assessment

| Gate | Result |
|---|---|
| Direct `GetFinancialReport` transport | PASS for bounded samples |
| Direct `GetAnnouncement` transport | PASS for bounded samples |
| Deterministic attachment→announcement join | PASS 4/4 primary filing families |
| PDF/XLSX/XBRL attachment retrieval | PASS in bounded samples |
| Direct bytes vs preserved official hashes | PASS 4/4 existing XLSX hashes |
| Explicit timezone/publication semantics | CONDITIONAL; Asia/Jakarta interpretation required |
| Older 2022 / early-2023 publication coverage | BLOCKED by public history response |
| Immutable correction/restatement chain | NOT DEMONSTRATED |
| Complete market-wide bounded PIT coverage | NOT PROVEN |

## Boundary

Do not bulk acquire financial statements, derive financial features, train or
score models, access protected outcomes, or touch other data lanes from this
checkpoint. The next possible step requires ChatGPT authorization for a small,
provenance-preserving adapter with fail-closed result-count/pagination,
announcement linkage, explicit timezone handling, statement-scope extraction,
and version preservation.

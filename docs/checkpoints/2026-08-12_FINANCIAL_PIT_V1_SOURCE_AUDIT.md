# Financial PIT V1 Source Audit — 2026-08-12

Status: bounded source audit complete; no bulk acquisition authorized.

Branch: `data/financial-pit-v1`
Base before documentation: `b442a29cb24bdb4f29c4907b64ba26c8158951db`
Evidence directory (outside Git): `D:\Documents\Project\idx-trade-financial-pit-20260812`

## Decision summary

| Gate | Result | Meaning |
|---|---|---|
| Source discovery | USABLE | Zapi wrapper and raw passthrough resolve the official IDX financial-report source and attachment metadata. |
| Publication-time PIT | CONDITIONAL | A representative join to official issuer-announcement timestamps works, but the public announcement history is retention-limited and the source does not carry an explicit timezone field. |
| Structured facts | USABLE FOR BOUNDED SAMPLE | Official XLSX/XBRL-style files expose period, scope, duration and structured statement content for the sample. A universal extractor was not implemented. |
| Complete 2021–2026 coverage | INCOMPLETE | Financial-report inventory rows exist, but publication-time linkage, revision completeness and full issuer coverage are not proven for the whole range. |

Overall verdict: `CONDITIONAL_PASS_SOURCE_DISCOVERY_ONLY_NO_GO_FOR_COMPLETE_FINANCIAL_PIT_ACQUISITION`.

No derived features, model work, realized-outcome access, or bulk financial-statement acquisition was performed.

## Preflight

- Focused: `python -m pytest tests/test_financial_pit.py -q` → **8 passed**.
- Full: `python -m pytest -q -rA` → **479 passed, 0 failed, 3 warnings, 29.02s**.
- The warnings are existing pandas `FutureWarning`s in `src/idx_trade/curated_identity.py:152` and `src/idx_trade/tradability_anchor_reconstruction.py:289`; no Financial PIT test failed.

## Resolved source path

The Zapi documentation identifies the IDX financial-report wrapper and raw passthrough as:

- wrapper: `GET /v1/finance:idx/financial-report`
- raw passthrough: `GET /v1/finance:idx/raw`
- upstream path: `ListedCompany/GetFinancialReport`
- required upstream query shape: `periode=TW1|TW2|TW3|audit`, `year=YYYY`, `indexFrom`, `pageSize`, `reportType=rdf`, optional `kodeEmiten`.

The official IDX attachment path is returned in `File_Path`, for example:

`/Portals/0/StaticData/ListedCompanies/Corporate_Actions/New_Info_JSX/Jenis_Informasi/01_Laporan_Keuangan/02_Soft_Copy_Laporan_Keuangan//Laporan Keuangan Tahun 2024/Audit/BBCA/FinancialStatement-2024-Tahunan-BBCA.xlsx`

The corresponding issuer-announcement metadata path is `ListedCompany/GetAnnouncement`. It supplies the announcement reference and `TglPengumuman`, which is the binding publication-time candidate for PIT. `created_at` is not used because it can be later or reflect re-indexing/migration.

Direct `www.idx.co.id` requests returned HTTP 403 from this network. The same official IDX attachment paths were acquired through the accessible `block.idx.id` mirror; the original `www.idx.co.id` URL remains the canonical source URL in the evidence mapping. This is a transport limitation, not a claimed source disagreement.

## Wrapper/raw/direct cross-check

Four representative records were checked across liquid/large, newer and older issuers and different periods:

| Issuer/period | Wrapper vs raw record | Attachment list | Issuer announcement join | Official XLSX bytes |
|---|---:|---:|---:|---:|
| BBCA FY 2024 | exact | exact, 11/11 | `003/ACT/2025`, 2025-01-23 17:30:34 | exact |
| BBCA Q1 2025 | exact | exact, 5/5 | `008/ACT/2025`, 2025-04-23 17:28:34 | exact |
| AADI FY 2024 | exact | exact, 9/9 | `AAI/009/III-25/corsec`, 2025-03-04 18:44:28 | exact |
| TLKM 9M 2025 | exact | exact, 7/7 | `Tel.36/LP 000/COP-M0000000/2025`, 2025-10-30 20:20:21 | exact |

Result: wrapper/raw parity **4/4**; official announcement linkage **4/4**; official XLSX byte equality between financial-report and announcement attachment **4/4**.

Representative official attachment SHA-256 values:

- BBCA FY 2024: `0fb2f5ae05e4a9b90f593500ad251260d21d2e4cf0d2b5e4280da2d335d05126`
- BBCA Q1 2025: `6500e5683e981aee063bb5ae752bb147725f8d1a2148a09c9e698691381922bb`
- AADI FY 2024: `b6ff2117193410503510c154190f02e5530fb8cc7524368a09ba811b58bd5642`
- TLKM 9M 2025: `65ffef8eecf97b2e5bddca5a3047d1e62308be1244525c48b92d9958aad03ff3`

The captured raw evidence remains outside Git. The four raw passthrough SHA-256 values are recorded in the handoff.

## PIT timestamp semantics

For all four cross-checks, financial-report `File_Modified` matches the issuer-announcement `TglPengumuman` to the available precision. The source timestamp is a naive IDX-local timestamp; the payload does not include a timezone field. Therefore the canonical ingestion rule must explicitly interpret it as `Asia/Jakarta` and convert to UTC-aware time before passing it to the PIT contract. Fiscal period end, filename date, board-signature date, and `created_at` must not substitute for `published_at`.

One important example is BBCA Q1 2025: the workbook board statement date is 2025-03-23, while the public announcement timestamp is 2025-04-23. The latter is the PIT publication candidate.

## Period and statement semantics

The sampled official XLSX/XBRL-style files expose explicit scope and period fields:

- `TW1` maps to Q1 and uses a duration from 1 January through 31 March.
- `TW2` maps to H1 and uses a duration from 1 January through 30 June.
- `TW3` maps to 9M and uses a duration from 1 January through 30 September.
- `audit` maps to FY and uses a duration from 1 January through 31 December.
- Q1/H1/9M income-statement and cash-flow durations are cumulative YTD in the sample; no standalone-quarter transformation was applied.
- `Entitas grup / Group entity` and `Entitas tunggal / Single entity` are explicit. The representative mapped rows are `CONSOLIDATED`; consolidated and separate statements must remain separate contracts.
- Files expose XLSX plus, depending on issuer/period, PDF, `inlineXBRL.zip`, and `instance.zip`. Older and newer workbook layouts differ, so field extraction must be version-aware.

## Bounded census

The successful bounded metadata census used 24 calls: years 2021–2026 × `tw1`, `tw2`, `tw3`, `audit`, with `length=20` and `start=0`. The endpoint rejects the attempted `length=1000`; the returned `records_total` values below are endpoint totals, not a claim that all rows were downloaded.

| Year | Q1 (`tw1`) | H1 (`tw2`) | 9M (`tw3`) | FY (`audit`) |
|---:|---:|---:|---:|---:|
| 2021 | 710 | 755 | 729 | 793 |
| 2022 | 754 | 812 | 771 | 858 |
| 2023 | 796 | 880 | 819 | 903 |
| 2024 | 684 | 923 | 854 | 934 |
| 2025 | 858 | 947 | 875 | 930 |
| 2026 | 854 | 814 | 0 | 1 |

Every successful non-empty page had 20 rows, 20 sampled tickers and XLSX availability. The 2026 `audit` row is `IMFI` and its attachment names/report content describe FY 2025, demonstrating that the report-year parameter is not sufficient by itself to establish fiscal-period identity. `tw3=0` is consistent with the capture date of 2026-08-12 being before the 2026 9M reporting season.

The financial-report endpoint therefore demonstrates broad metadata discovery, but not complete issuer-level acquisition, publication-time coverage, or period correctness without pagination and announcement/file binding.

## Public announcement retention and revisions

The captured issuer-announcement responses advertise a current three-year range of `2023-08-12` through `2026-08-12`. This means the 2021–2022 report rows, and the pre-2023-08-12 part of 2023, cannot currently be proven PIT-visible through the public issuer-history response even when the financial-report inventory still returns an attachment row.

The sampled BBCA, AADI and TLKM announcement histories exposed separate correction announcements for some non-financial disclosures, but no representative financial-statement restatement version with an independently preserved filing version was found. The financial-report endpoint returns one current record per issuer/period and does not expose a demonstrated immutable revision chain. Consequently:

- later corrections must be retained as separate candidate filings when discovered;
- no later row may overwrite an earlier filing;
- revision completeness is **not proven** for 2021–2026.

Strongest defensible publication-time sample window: `2023-08-12` through `2026-07-31` for issuers whose announcement-to-file join is independently completed. A complete market-wide bounded window has **not** been established.

## Contract mapping smoke check

A four-filing representative sample (`BBCA` FY 2024, `BBCA` Q1 2025, `AADI` FY 2024, `TLKM` 9M 2025) was mapped in memory to `canonicalize_financial_filings` and filing-bound duration facts. `financial_filings_asof` and `financial_facts_asof` passed the before/at-publication visibility checks. No artifact was written to the repository and no derived metric was calculated.

## Remaining blockers / next safe step

1. Build a paginated official acquisition adapter that joins every financial-report row to the immutable issuer-announcement publication record and preserves all matching attachment versions.
2. Make the source-timezone rule explicit before canonicalization; do not pass naive IDX-local strings as UTC.
3. Add version-aware structured-file normalization for old/new XLSX/XBRL layouts, with explicit period and consolidated/separate checks.
4. Resolve an official historical announcement/archive path for reports older than the public three-year issuer-history boundary, or leave those filings unknown.
5. Establish a revision/restatement discovery policy before claiming complete PIT coverage.

No mass backfill is authorized by this audit.

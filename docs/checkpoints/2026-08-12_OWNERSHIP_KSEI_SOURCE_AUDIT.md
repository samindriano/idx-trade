# Ownership / KSEI V1 — bounded source audit

Date: 2026-08-12
Branch: `data/ownership-ksei-v1`
PR: #23
Status: `CONDITIONAL_SOURCE_READY_PIT_BLOCKED`

## Scope and boundary

This was a bounded source/semantics audit only. It did not bulk-acquire years of
ownership files, add ownership features, access outcomes, or change the
Ownership/KSEI contract. The API key was read from `ZAPI_API_KEY` and was never
written to the repository or evidence files.

Raw captures and downloaded official files are outside Git at:

`D:\Documents\Project\idx-trade-ownership-ksei-20260812`

## Validation run

- Focused: `python -m pytest tests/test_ownership_pit.py -q` → **7 passed**.
- Full: `python -m pytest -q -rA` → **478 passed, 0 failed, 3 warnings, 29.57s**.
- Warnings are the existing pandas `FutureWarning`s in
  `src/idx_trade/curated_identity.py:152` and
  `src/idx_trade/tradability_anchor_reconstruction.py:289` (two tests).
- No implementation fix was required.

## Source inventory

### Zapi IDX ownership files

Discovered wrapper:

`GET https://api.zpi.web.id/v1/finance:idx/ownership-files`

Documentation: [Zapi IDX API](https://zpi.web.id/api/finance/idx).

Parameters observed: `category`, `length` (maximum 200), and `start`. Categories
are `lima-persen`, `satu-persen`, `klasifikasi`, and `tipe`.

The wrapper returns official IDX media metadata, not workbook contents. The
returned `source` is `KSEI`, and the returned `url` is an official IDX Media
URL. Representative metadata response hashes:

| Query | Rows | Date coverage observed | Response SHA-256 |
|---|---:|---|---|
| all categories | 68 | 2026-05-29–2026-08-10 | `e435a318a6c6d0c2a923cb63b3103f5f95e8f63992beb69b43ff956cbc0130f9` |
| `lima-persen` | 50 | 2026-05-29–2026-08-10 | `8cb8f86dc29b83f9c346c16e845fffdc63d3623a3a076cd6a10fffce212c859b` |
| `satu-persen` | 6 | 2026-01–2026-07 | `3affe7119a9b52c860339ea69ff909c70576be031bfabf7adf3b414fefb1a2cc` |
| `klasifikasi` | 5 | 2026-01–2026-07 | `c303c90c2cc050941043e6611179082722a98a103e4fb355bee51491051071fb` |
| `tipe` | 7 | 2026-01–2026-07 | `30082345d11b07d027151a4969c23f1e52f933b70a2d7c4ad4a438c6400b91cf` |

Four representative official IDX workbooks were fetched using the exact Media
paths. The canonical `www.idx.co.id` host returned HTTP 403 from this runtime;
the same official Media paths on the IDX `block.idx.id` host returned XLSX
bytes. The canonical URLs, retrieval URLs, and hashes are preserved in the
outside-Git evidence directory.

| Category | Representative file | Retrieved bytes | SHA-256 |
|---|---|---:|---|
| >5% (`lima-persen`) | `peng-2026-07-30-00043-lima-persen.xlsx` | 393,142 | `17101bb2b1df91ae4f31f51d72b1217b9b89201adde56d2011016d27080b30db` |
| >1% (`satu-persen`) | `peng-2026-07-00016-satu-persen.xlsx` | 574,772 | `15e705af3644508968b37138f51ad314f96e47d6b96b4567dfcdd7272c0d0cc3` |
| investor classification | `peng-2026-07-00017-klasifikasi.xlsx` | 265,502 | `ca5a947298b916b2726d238a23a76ae37700feffda3b6869b3d4efa69cd15b95` |
| investor type | `peng-2026-07-00018-tipe.xlsx` | 249,578 | `6e908a9dc64041d8f67de1197bd9bb061c13a3a21a5caccd4d7e9d9e9b2902ee` |

The workbooks establish the following semantics:

- `lima-persen`: named holders and account-level rows for holdings above 5%;
  the sample has 3,122 rows across 840 issuers.
- `satu-persen`: named holders and share counts/percentages above 1%; the
  sample has 7,193 rows across 961 issuers. It is intentionally sparse.
- `klasifikasi`: per-security share counts by detailed investor-classification
  columns; the sample has 962 securities.
- `tipe`: per-security share counts by local/foreign investor type and `<5%` /
  `>=5%` bands; the sample has 1,007 equities.
- The `tipe` workbook explicitly says KSEI is not authorized to determine free
  float. No free-float value is therefore accepted from this source family.

The IDX API's `publishedAt` is an exact date for daily >5% files and a `YYYY-MM`
label for the monthly categories. No time-of-day or timezone is exposed.

### Zapi KSEI

Discovered wrappers:

- `GET https://api.zpi.web.id/v1/finance:ksei/ownership`
- `GET https://api.zpi.web.id/v1/finance:ksei/demographics`
- `GET https://api.zpi.web.id/v1/finance:ksei/distribution`

Documentation: [Zapi KSEI API](https://zpi.web.id/api/finance/ksei).

The `ownership` endpoint is per-security, not market-only. It accepts `date`
(exact date or month), optional one-security `code`, `type=EQUITY`, `length`, and
`start`. A no-code query returned totals of 1,007, 1,002, and 1,002 equities
for July, June, and May 2026 respectively. The two aggregate endpoints are
different: `demographics` is market-wide investor demographics and
`distribution` is market-wide domestic regional distribution.

For each security, the KSEI ownership response exposes:

- `outstanding` and `recordedTotal` in shares;
- local and foreign totals in shares;
- nine local and nine foreign investor categories: insurance, corporate,
  pension fund, financial institution, individual, mutual fund, securities,
  foundation, and others;
- `foreignPctOfRecorded` and `foreignPctOfOutstanding` as percentages in the
  range 0–100;
- a price field, which is not treated as an ownership metric.

The response's `timestamp` was 2026-08-11T18:22–18:23Z for all sampled calls.
It is the Zapi access/response timestamp, not a source publication timestamp.

### Direct official KSEI

The official archive page is [KSEI Download Holding Composition](https://web.ksei.co.id/archive_download/holding_composition?setLocale=en-US).
It labels the files as Holding Composition by date and links, for example, to
`https://web.ksei.co.id/Download/BalanceposEfek20260731.zip`.

Each ZIP contains a pipe-delimited `BalanceposYYYYMMDD.txt` with `Date`,
`Code`, `Type`, `Sec. Num`, `Price`, nine local categories plus `Total`, and
nine foreign categories plus `Total`. The file date is the holding-position
date. The archive/file contains no publication time or timezone.

Bounded direct-file inventory:

| File date | ZIP bytes | ZIP SHA-256 | All instruments | EQUITY rows |
|---|---:|---|---:|---:|
| 2021-12-30 | 85,579 | `49da96f09b563e6180040034a89f7e6382fadf256f1ade8d927cc86564465eba` | 2,198 | 803 |
| 2022-12-30 | 93,868 | `491d7e5426a3effd33a26f6286e1e56e03528a5eb249a874597ba456246bdd8a` | 2,462 | 861 |
| 2023-12-29 | 105,132 | `23c6039b9f72207607d2d9955337c1c9b3441f6b5842c5e545a8e687bc1be528` | 2,862 | 939 |
| 2024-12-30 | 113,330 | `5e29ac2bc6fe7e570b4800e4f9580e7554f16c067dfd507fda2211045213c7b2` | 3,273 | 979 |
| 2025-12-30 | 122,338 | `72208a93690019c9a4b2316b91dc0a1aa1e9438be570d09d169ed1e77c04338a` | 3,624 | 1,002 |
| 2026-05-29 | 124,565 | `c487ac486bf1f22302a8eb942c6a27ccd4ac000d56b89fecb89651c406eaa992` | 3,712 | 1,002 |
| 2026-06-30 | 126,396 | `bab7447ed7d94766d67ecef7a8585951775e4ca6a82154c7326c22f4fc7788aa` | 3,851 | 1,002 |
| 2026-07-31 | 125,974 | `16b4c8629e76b34d764c0513fd802201bfc421a2d9bf6059128903e80d89fa15` | 3,802 | 1,007 |

All sampled direct files had unique instrument codes and passed non-negative
value and local/foreign-total arithmetic checks. The 2021 file contains
decimal-valued legacy fields, so validation used numeric tolerance rather than
an integer-only parser.

## Direct parity and invariants

The direct KSEI files were compared with Zapi `ownership` for BBCA, AADI, and
BBRI at 2026-05-29, 2026-06-30, and 2026-07-31. The comparison covered
`Sec. Num`/`outstanding`, `Price`, nine local categories plus total, and nine
foreign categories plus total:

- 3 tickers × 3 month-end dates × 22 fields = **198/198 exact matches**;
- Zapi `recordedTotal = local.total + foreign.total`: **12/12** sampled
  responses, including the 2026-07-30 daily responses;
- both Zapi foreign percentage identities matched to two decimals:
  **12/12** for recorded-total denominator and **12/12** for outstanding
  denominator;
- two immediate repeated BBCA 2026-07-31 Zapi calls had identical core
  payloads after removing the access timestamp.

The 2026-07-30 Zapi daily response is not directly comparable to the official
KSEI public monthly archive because that archive exposes month-end files. It is
therefore recorded as source-consistent but not independently byte/field
cross-checked for that day.

## PIT, revisions, and missing rows

The source date is not enough to populate the Ownership V1 `published_at`:

- official KSEI archive pages/files expose a position date only;
- official IDX ownership metadata exposes date or month granularity only;
- Zapi `timestamp` is retrieval time, not upstream publication time;
- no timezone-resolved publication timestamp was found.

The official >1% workbook disclaimer states that updates to an earlier report
are applied to that report period. This proves that replacement/correction is a
real possibility, but no immutable revision identifier or historical version
listing was exposed in this bounded audit. A stable repeated Zapi response is
not evidence that older files are immutable.

Missingness is category-specific and must not be converted to zero:

- missing `lima-persen`/`satu-persen` rows mean no qualifying named holder was
  returned, or a source/reporting gap; they do not mean zero ownership;
- `klasifikasi` can have fewer security rows than `tipe` (962 vs 1,007 in the
  July sample), so absent classification is unknown, not zero;
- a no-code Zapi total is a source result for that requested period, not proof
  that a separately supplied historical universe is complete;
- absent issuer/file and missing Zapi rows require explicit reconciliation to
  the official KSEI/IDX file and security universe.

## Verdict

| Gate | Result | Reason |
|---|---|---|
| source discovery usable | **PASS** | IDX ownership-file and KSEI wrappers, official file paths, fields, and raw provenance were identified |
| per-security ownership usable | **PASS, bounded** | KSEI local/foreign and nine categories are per-security; IDX files add >1%, >5%, named-holder, classification, and type views |
| PIT timing usable | **FAIL / blocked** | no defensible timezone-aware publication timestamp; Zapi access timestamp cannot be substituted |
| historical coverage complete | **INCOMPLETE** | direct KSEI files are demonstrably available for sampled dates from 2021-12 through 2026-07, but month-by-month acquisition completeness and revision history were not established |
| ready for bulk acquisition | **NO-GO** | bulk acquisition must wait for a publication-time/version strategy and an explicit month/file census |

Strongest defensible statement: the source family has a **semantic availability
envelope covering the sampled dates 2021-12-30 through 2026-07-31**, with direct
KSEI URL retrieval also responding for several older dates. This is not a
complete historical research window because the full monthly file census,
publication knowledge times, and immutable revision lineage are still missing.

No ownership snapshot was materialized into the production PIT contract: doing
so would require inventing `published_at`, which is prohibited by the contract.

No model, feature, outcome, OPEN, PIT-sector, Historical Universe, Corporate
Actions, Financial PIT, Foreign Flow, Path Risk, execution/PnL, or `main` work
was touched.

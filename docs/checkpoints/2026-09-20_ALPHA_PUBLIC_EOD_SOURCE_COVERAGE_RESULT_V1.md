# Public IDX EOD/IPO Source Coverage — Result V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `CAPABILITY FOUND / ADMISSION BLOCKED`

## Question

Can newly acquired public IDX-derived snapshots add evidence about historical
population coverage, the CNTX panel gap, and the six current anchor tickers not
present in the newest acquired EOD snapshot, without being mistaken for PIT or
survivorship authority?

No protected outcome, feature target, canonical data, production, cloud,
capture, telemetry, scheduler, or authenticated provider state was accessed or
changed.

## Acquired sources and identity

| Source | Pinned identity | Acquired surface |
|---|---|---|
| [Pholenk/IDX-Dataset](https://github.com/Pholenk/IDX-Dataset) | commit `9bb3b26bd28ab46bc2f3e74a7c03805ce053301b`; tree `fdf171acdbbd0d752e2611e0f0f01a6e72bc7703`; `metadata.json` SHA-256 `8fc0631b...31cb89d` | 983 ticker CSVs, 1,289,820 rows, 2020-01-02 through 2026-05-29 |
| [wildangunawan/Dataset-Saham-IDX](https://github.com/wildangunawan/Dataset-Saham-IDX) | commit `bc0ac7712ce5e46f1067349e13ab9f338883c6c4`; tree `b85e5df6bd941ee1798d78ef1110efd25c66a547` | explicit `Saham/Semua` folder: 958 ticker CSVs, 1,078,040 rows, 2019-07-29 through 2025-02-21 |
| [ricotandrio/web-indonesia-ipo-data](https://github.com/ricotandrio/web-indonesia-ipo-data) | commit `5f1ca215b29e0bb962b4a09217414a2619c20fd8`; tree `b16bd78107225b37f08a2156b8b43108e331064b` | 251 IPO ticker files; `information.json` says updated 28 June 2026 |
| [NeaByteLab/IDX-API](https://github.com/NeaByteLab/IDX-API) | commit `910b8db70893b93920a1bba331d00a1a245907c6` | source-code discovery of issuer, delisting, new-listing, and relisting routes; no live data acquired from this adapter |
| [IDX official current company profiles](https://www.idx.id/primary/ListedCompany/GetCompanyProfiles?start=0&length=9999&code=) | ordinary public GET; raw SHA `bdca057527fa061fd2318f7c9aa6c4f2c508d50a98f013c38ea1a7c4c9ad2312` | 962 current records, 962 unique codes; current identity snapshot only |

The Pholenk EOD snapshot has zero duplicate `(Date,Ticker)` keys, 156,317
zero-volume rows, 1,045,981 rows with at least one zero OHLC field, 427 files
with changing listed-share values, and 78 files with multiple names. These are
raw source characteristics, not corporate-action or identity conclusions.

## CNTX and population interpretation

Both EOD snapshots contain CNTX. The newer Pholenk file has 1,537 rows from
2020-01-02 through 2026-05-29, including 824 zero-volume rows. The frozen
anchor has 458 ACTIVE and 800 NO_TRADE CNTX rows. Therefore the earlier finding
is sharpened:

- the panel/anchor replay proves observed-panel coverage only;
- CNTX is not absent from every acquired public EOD source;
- the panel’s 981,940-key zero mismatch still says nothing about complete
  historical population or survivorship safety;
- public ticker-file availability does not establish that the historical
  ticker set is complete, PIT-correct, issuer-continuous, or CA-safe.

## Snapshot overlap and six-ticker gap

The Pholenk snapshot date is 2026-05-29. Exact ticker/date presence is:

| Surface | Through 2026-05-29 | Full frozen surface |
|---|---:|---:|
| Anchor | 1,060,071 / 1,062,767 (`99.7463%`) | 1,060,071 / 1,104,064 (`96.0154%`) |
| Panel | 943,283 / 945,693 (`99.7452%`) | 943,283 / 981,940 (`96.0632%`) |

The six missing ticker files are `BACH`, `EMMI`, `JECX`, `JELI`, `PRDL`, and
`RANS`. The independent IPO dataset declares exactly those six as its new-stock
list, with June 2026 book-building windows; only JELI has a populated listing
date (`07/07/2026`) in the acquired JSON. This is strong bounded evidence that
the six-file difference is a snapshot-timing/new-issue gap, not evidence that
the anchor rows are impossible or invalid. It is not a historical population
completeness contract.

## Official-source discovery and current-directory boundary

The pinned IDX-API source code documents `GetCompanyProfiles`, monthly
`LINK_DELISTING`, monthly `LINK_STOCK_NEW_LISTING`, and `GetRelistingData`
routes. The official IDX delisted-company page exposes fields for code, company,
listing date, delisting date, shares, market cap, regular price, and last date.
An ordinary unauthenticated GET to the official current-company directory
returned HTTP 200 and was retained as a hash-bound raw artifact. It contains
962 unique current codes and exactly matches the prior official current
snapshot by code and listing date. The official current codes are a subset of
the 980-code anchor surface; 18 historical-anchor codes, including CNTX, are
not current-directory records. This is current-snapshot evidence only. It
does not provide daily historical membership, issuer/ISIN transitions,
publication/available-at time, revisions, or corporate-action basis.

The detailed current-directory audit is
`docs/checkpoints/2026-09-20_ALPHA_OFFICIAL_IDX_DIRECTORY_AUDIT_RESULT_V1.md`.

## Admission result

| Authority | Result |
|---|---|
| Historical population completeness | `UNKNOWN` |
| Survivorship safety | `UNKNOWN` |
| PIT/publication/available-at time | `MISSING` |
| Issuer/ISIN continuity and ticker reuse | `MISSING` |
| Corporate-action effective basis | `MISSING` |
| Historical research admission | `BLOCKED` |

The durable evidence record is
`research_knowledge/public_eod_source_coverage_v1.json`; the full raw-source
audit artifact is
`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_public_eod_source_coverage_v1.json`
with SHA-256
`44522e840f0e639c6616f13f54626a69408c5df625cc61ee7f283a8826dfe94b`.

## What would reopen this boundary

An authoritative population-wide PIT security master or equivalent contract
with complete daily membership, delisted/relisted/ticker-reuse handling,
issuer/ISIN continuity, row-level publication/knowledge time, corporate-action
effective-basis semantics, and revision/vintage policy. More ticker files from
the same snapshot family would not satisfy that requirement.

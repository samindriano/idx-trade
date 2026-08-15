# Statutory Free Float Reconstruction V1 — bounded result

Date: 2026-08-15
Branch: `data/idx-statutory-free-float-reconstruction-v1`
Prepared parent: `414f4c232326f4da6e3fb1430d824eb1329877e7`

## Decision

Final verdict: `STATUTORY_FREE_FLOAT_SOURCE_REMEDIATION_REQUIRED`

The bounded source is useful for official reported free-float diagnostics, but
the exact official rule attachments and a defensible history back to 2021 were
not recovered in this run. No reconstructed point estimate is promoted.

## Transport and provenance

The accepted IDX announcement metadata captures expose the canonical attachment
transport through `attachments[].FullSavePath`, for example:

`https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/<YYYYMM>/<hashed-file>.pdf`

The selected official static attachments were downloaded directly from the
exact captured URLs. All 34/34 bounded attachment requests returned HTTP 200,
PDF bytes, and were SHA-256 pinned externally. The external artifact root is:

`D:\Documents\Project\idx-statutory-free-float-reconstruction-20260815-v1`

The official metadata endpoint used for discovery was probed with the accepted
`ListedCompany/GetAnnouncement` parameter contract on 2026-08-15. Both the
February 2026 broad probe and the March 2026 `Kep-00045` keyword probe returned
HTTP 503. Their response bytes and hashes are preserved under the external
`search/` directory. Existing local official captures were reused; no bulk
announcement crawl was started.

## Official rule semantics observed

The recovered official market reports state the following criteria; they are
not substitutes for the unrecovered rule attachments:

* `Peng-S-00006/BEI.PLP/02-2026`, position 2025-12-31, published 2026-02-19:
  the report describes the then-applicable 50,000,000-share and 7.5% minimum
  for the cited I-A/I-V provisions, plus the 300-SID-holder requirement.
* `Peng-S-00011/BEI.PLP/04-2026`, position 2026-03-31, published 2026-05-07:
  the report cites `Kep-00045/BEI/03-2026` and
  `SE-00004/BEI/03-2026`, describes 50,000,000 shares and 15% for the
  applicable I-A boards, 7.5% for I-V, and 300 SID holders. It also states the
  transition treatment for pre-existing companies, including the 12.5%/15%
  staged thresholds for the relevant high-capitalization group.

The exact official bytes/locators for `Kep-00045/BEI/03-2026`,
`SE-00004/BEI/03-2026`, and `Kep-00101/BEI/12-2021` remain unresolved. No
inference from HSC, >=1% ownership, investor type, current Company Profile, or
`100% - holders` was used.

## Market-wide report recovery and history depth

Two official status reports were recovered, each with a main PDF and an
attachment. The attachment tables parse to 956 company rows each:

| Report | Position date | Publication date | Parsed rows | Status |
|---|---:|---:|---:|---|
| `Peng-S-00006/BEI.PLP/02-2026` | 2025-12-31 | 2026-02-19 | 956 | official bytes recovered |
| `Peng-S-00011/BEI.PLP/04-2026` | 2026-03-31 | 2026-05-07 | 956 | official bytes recovered |

The preserved official announcement capture set contains free-float/sanction
records from April 2024 through August 2026. It does not prove 2021–2023
coverage. Because the live historical endpoint was unavailable and no exact
official 2021–2023 attachment locator was preserved, the historical cadence
back to 2021 is `UNRESOLVED`, not complete.

## Issuer-level LBRE bounded sample

The sample covers DCII, WBSA, RLCO, BREN, BBCA, TLKM (ordinary comparison),
and MAYA. It contains 15 exact announcement/attachment records, including 5
records explicitly marked `KOREKSI`. All 15 main LBRE PDFs contain an explicit
`Informasi Saham Free Float` section with current/previous columns and an
explicit reported free-float share count and percentage.

The observed schema includes, where applicable:

* total listed shares at month end;
* non-warkat/scripless ownership;
* controller and controller-affiliate buckets;
* directors/commissioners;
* treasury shares;
* restricted/lock-up shares;
* venture-capital/private-equity shares;
* seized or blocked shares;
* specifically approved public-beneficiary shares;
* reported free-float shares and percentage.

The exact normalized sample, evidence locations, source URLs, announcement
references, metadata hashes, attachment hashes, and correction lineage are in
`normalized/issuer_reported_free_float_benchmark.csv` under the external root.
The internal arithmetic check of reported percentage versus reported shares /
listed shares is diagnostic only; it is not used to reconstruct free float.

Coverage classification for the 15 issuer records:

| Classification | Count | Meaning |
|---|---:|---|
| `OFFICIAL_REPORTED` | 15 | explicit issuer-reported free-float fields found |
| `VERIFIED` | 0 | no record promoted as a complete share-class reconstruction |
| `BOUNDED` | 15 | official reported value available, but all relevant shares were not proven classified for a point estimate |
| `UNRESOLVED` | 0 | no missing explicit report field in this bounded sample |

`BOUNDED` is deliberately the reconstruction result even when the issuer
report supplies an official number. It prevents the diagnostic from claiming
that the agent independently classified every relevant share.

## Artifact integrity

External artifact manifest:

`D:\Documents\Project\idx-statutory-free-float-reconstruction-20260815-v1\artifact_manifest.json`

Manifest SHA-256: `ff25cefed69af8cd221530a23f6fc31e85e0c510a21ef5bfb78526d618a45454`

The manifest covers 88 external files, including selected raw metadata
captures, 34 official attachment files, extracted text, probe responses,
normalized benchmark output, source inventory, and audit summary. Bulk/raw
files remain outside Git.

## Boundaries respected

No statutory free-float point estimate, HHI, effective-supply feature,
Foreign Flow integration, model, outcome access, or canonical price/model
artifact was changed.

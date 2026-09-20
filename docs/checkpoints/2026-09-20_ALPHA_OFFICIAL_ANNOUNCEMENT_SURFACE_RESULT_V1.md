# IDX-Trade official announcement surface result

Date: 2026-09-20
Branch: `codex/alpha-available-data-20260919`
Scope: outcome-blind public-source and data-authority research only

## Verdict

`PASS_OFFICIAL_ANNOUNCEMENT_SURFACE_RESEARCH_ONLY`

This is a bounded official event-discovery capability result. It is not an
admission of a complete lifecycle, PIT population, issuer identity, or
corporate-action authority.

## Evidence

The ordinary public IDX endpoint
`https://www.idx.id/primary/NewsAnnouncement/GetAllAnnouncement` returned
structured results for six keyword probes:

| Keyword | ItemCount | Pages | Result boundary |
|---|---:|---:|---|
| Penghapusan Pencatatan | 10 | 1 | bounded search result |
| Pencatatan Kembali | 4 | 1 | bounded search result |
| Perubahan Nama | 182 | 2 | page 1 of 2 retained |
| Perubahan Kode | 2 | 1 | one result has an empty Code field |
| Penggabungan | 175 | 2 | page 1 of 2 retained |
| Pemecahan Saham | 19 | 1 | bounded search result |

The classification query returned 11 records: eight company-specific records
(DEFI, LAPD, MDKA, MGNA, PALM, PANI, PNGO, SWID) and three exchange-wide
packages for 2024-2026. The exchange-wide package bytes match the existing
official sector archive exactly, so they are not new annual payloads.

## New authority boundary

Four downloadable company-specific documents (DEFI, PANI, PNGO, SWID) state
that the change became effective on 24 June 2024, while the API metadata gives
22 January 2025 as the publish date. Publication time and effective-date text
must therefore remain separate. Attachment URLs also require content checks:
7 of 17 retained company attachment responses were non-PDF or non-200, and
multiple successful links had the same PDF hash.

The lifecycle keywords are semantically mixed: two of four `Pencatatan Kembali`
results concern board/officer structure rather than security relisting, and
`Penghapusan Pencatatan` mixes treasury/security cancellations, go-private
plans, and explicit listing events. The date-filter probe returned HTTP 503.
It is recorded as a bounded source failure and is not used to claim date-range
completeness. The retained second pages reconcile the reported counts for
`Perubahan Nama` (182 unique IDs, 2023-07-10 through 2026-09-01) and
`Penggabungan` (175 unique IDs, 2023-07-03 through 2026-09-02). This validates
pagination for those two queries only; it does not turn keyword results into a
complete historical event ledger.

The 182 name-change results contain 108 unique codes, 43 repeated codes, and
11 broker records. The 175 merger results contain 71 unique codes and 32
repeated codes. These are announcement/document counts, not counts of issuer
identity transitions or underlying corporate events.

## Admission

Allowed: bounded official event discovery, publication-versus-effective timing
audits, and source-design research.

Blocked: replacing the daily PIT universe, inferring survivorship or ticker
reuse, assuming issuer/ISIN continuity, silently imputation of effective dates,
or predictive research admission.

Machine result: `research_knowledge/official_announcement_surface_v1.json`
External result SHA256:
`fe00c9eee8cd800d2d1b6c9c0154c9cd8450cc90e67c4260d7c4d04f0fd32818`

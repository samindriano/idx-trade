# Research checkpoint — PIT historical sector source research

Date: 2026-08-11 (Asia/Jakarta)
Status: `SOURCE_RESEARCH_RECORDED_NOT_AUTHORIZED`
Branch: `research/idx-ranking-v2-spec-v1`

## Question

Where should the project start to obtain a point-in-time-safe historical IDX-IC sector map for future sector-relative research?

## Key finding

The strongest reconstruction path is official IDX event history rather than a present-day sector snapshot.

IDX-IC became effective on 25 January 2021. The initial IDX announcement package (`Peng-00007/BEI.POP/01-2021`) included the classification guide and the listed-company classification list. IDX states that regular classification evaluation is performed annually around April-May, announced near the end of June, and becomes effective on the first trading day of July.

For newly listed companies, classification is determined from the prospectus and becomes effective when the company starts trading. Public reporting of the IDX launch also states that classification changes are announced on the IDX website.

This gives a natural event-sourced PIT reconstruction:

```text
initial IDX-IC baseline (25 Jan 2021)
        +
new-listing classification events (effective listing date)
        +
annual reclassification events (effective first trading day of July)
        +
any separately announced exceptional classification change
        =
effective-dated ticker -> IDX-IC history
```

## Primary sources to pursue

### 1. Initial official IDX-IC package — highest priority

Known official reference:

- IDX announcement `Peng-00007/BEI.POP/01-2021`, dated 13 January 2021;
- historically referenced IDX file path: `https://www.idx.co.id/media/9594/idx-industrial-classification.zip`;
- package is reported to contain the launch announcement, IDX-IC guide, and listed-company classification list.

A related sectoral-index announcement is `Peng-00012/BEI.POP/01-2021`, dated 21 January 2021.

The project should preserve the raw downloaded source plus SHA-256 and parse it into a baseline effective on 25 January 2021.

### 2. Annual June IDX sector/classification evaluations

IDX's own classification rules make the annual evaluation cycle the main historical change feed: evaluation in April-May, announcement at the end of June, effective first trading day of July.

Examples of announcement identifiers independently surfaced during source research:

- 2024: `Peng-00127/BEI.POP/06-2024`, dated 24 June 2024;
- 2025: `Peng-00111/BEI.POP/06-2025`, dated 23 June 2025.

The exact official IDX attachments for every year 2021-2026 should be located and hash-pinned. Do not infer unchanged classifications merely because a secondary website does not mention a ticker.

### 3. New IPO classification events

IDX states that for a newly listed company the classification is determined using its prospectus and is effective from the listing date.

For every ticker first listed after the latest baseline/evaluation snapshot, collect an official prospectus/listing source containing its IDX-IC assignment, or an official IDX classification/listing publication that provides the same information. The effective date is the first listing/trading date, not the following annual July evaluation.

### 4. Current official IDX list — validation only

IDX currently publishes a downloadable/listable `Daftar Saham` with sector filters. This is useful as a terminal-state reconciliation target, but it must not be backfilled historically.

The current classification can validate whether the accumulated event log reconstructs the present state.

### 5. IDX Data Services / Data Reference — escalation path

IDX Data Services offers direct/redistributed market data and an `IDX Data Reference` product for listed-company information. The public product page does not explicitly confirm that effective-dated historical IDX-IC classification is included.

Therefore this is a potentially cleaner paid/official source, but the project should first request/sample the exact schema and confirm that historical classification changes and effective dates are available before spending or treating it as authoritative for PIT sector history.

IDX also lists redistributors including RTI, IQ Plus, IDX Solusi Teknologi Informasi, Bloomberg, FactSet, Refinitiv and others. Redistributor history may be useful only if source lineage/effective-date semantics can be demonstrated.

## Secondary sources — discovery/cross-check only

Company press releases and sector-reference sites can help discover exact IDX announcement numbers and candidate reclassification events. They must not become the canonical classification source when the corresponding IDX source can be obtained.

Examples found during research include company releases citing the 2024 and 2025 IDX sector evaluation announcements and public reports describing specific July reclassifications.

Use them to locate primary documents, not to silently fill gaps.

## Proposed canonical event schema

```text
ticker
classification_code
sector_code
subsector_code
industry_code
subindustry_code
effective_from
effective_to
announced_at
source_type
source_ref
source_sha256
source_row_or_page
reason
```

`announced_at` and `effective_from` must remain separate. The model join should use the classification that is both effective and already knowable under the frozen PIT rule for the signal date.

## Recommended collection order

1. Recover and hash the January 2021 initial IDX-IC package.
2. Recover official annual June evaluation attachments for 2021-2026.
3. Diff successive annual states to identify reclassifications and verify effective dates.
4. Enumerate all IPOs between annual effective dates and recover their official initial IDX-IC assignments.
5. Search for any separately announced classification changes outside the regular annual cycle.
6. Build an event log, then materialize effective-dated intervals.
7. Reconcile the final state against the current official IDX stock/sector list.
8. Run coverage/conflict/PIT audit before any sector-relative feature or model experiment is authorized.

## Important scope advantage

The current research history is largely inside the IDX-IC era, so this source strategy should avoid needing a broad JASICA-to-IDX-IC historical bridge unless a future experiment deliberately extends before 25 January 2021.

The exact start date required by a future experiment must still be checked against the frozen research panel before implementation.

## Hard boundaries

This checkpoint does not authorize:

- scraping or silently ingesting unverified third-party sector histories;
- backfilling current sector labels into the past;
- running V3-D or a new sector-relative model;
- modifying frozen V3-B;
- accessing fresh-forward outcomes;
- changing the existing historical panel;
- purchasing/subscribing to IDX or redistributor data without a separate decision;
- treating current `Daftar Saham` as historical truth.

## Research conclusion

Start with the official January 2021 IDX-IC baseline package and official annual June classification/evaluation announcements. Reconstruct sector history as an effective-dated event log, then fill new-listing intervals from official prospectus/listing evidence. Use current IDX sector data only as terminal reconciliation and use commercial IDX Data Reference/redistributors only if the public-document reconstruction proves incomplete or too costly to maintain.

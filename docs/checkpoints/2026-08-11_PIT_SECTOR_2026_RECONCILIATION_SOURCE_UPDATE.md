# PIT Sector 2026 Reconciliation Source Update

Date: 2026-08-11
Branch: `data/idx-pit-sector-history-v1`
Status: `RECONCILIATION_LEAD_RECORDED_NO_CANONICAL_PROMOTION`

## Context

Canonical annual 2026 IDX-IC classification source remains:

- `Peng-00100/BEI.POP/06-2026`
- announced `2026-06-24`
- affected issuers: `ARGO`, `HRUM`, `PACK`
- explicit canonical effective date: unresolved
- status: `DISCOVERY_REQUIRED`

The canonical two-page document has already been inspected and contains no explicit effective-date statement.

## New reconciliation lead

External reporting that reproduces BEI index-evaluation data identifies:

- `Peng-00099/BEI.POP/06-2026`
- dated `2026-06-24`
- an index-evaluation package containing multiple index attachments/data.

Separate reporting on the sector-index evaluation states that `HRUM` moves into `IDXBASIC` and `ARGO` into the property/real-estate sector index, with the index changes effective `2026-07-01` and the evaluation period running through `2027-06-30`.

This makes `Peng-00099/BEI.POP/06-2026` a high-value **reconciliation-source candidate** for the 2026 classification event.

## What this does NOT establish

Do **not** set canonical `IDX_IC_ANNUAL_CLASSIFICATION_2026.effective_from = 2026-07-01` from this discovery alone.

Reasons:

1. `Peng-00099` is an index-evaluation lead, not the canonical issuer-classification announcement `Peng-00100`.
2. The official IDX attachment URL and raw SHA-256 for `Peng-00099` have not yet been recovered in this pass.
3. No official document has yet been bound under the existing multi-document linkage contract to canonical source id/ref/raw SHA for `Peng-00100`.
4. Index applicability and issuer-classification effective time must remain distinct unless an official linked document explicitly establishes the relationship.

Therefore canonical inventory remains fail-closed: `4 ready / 4 blocked`.

## Next retrieval target

Use the IDX announcement endpoint already identified in the preceding checkpoint:

```text
/primary/ListedCompany/GetAnnouncement
```

Priority queries:

- `ARGO`, `HRUM`, `PACK` around `2026-06-24` through `2026-06-25`;
- exchange-wide announcements around `2026-06-24` for `Peng-00099`;
- recover attachment `FullSavePath`, acquire from official IDX HTTPS host, and SHA-pin before any provenance promotion.

If `Peng-00099` itself explicitly links the affected sector-index changes to the `Peng-00100` issuer-classification event, evaluate it against the existing multi-document evidence contract. Otherwise retain it only as reconciliation evidence.

## Boundary

No parser/materialization, IPO census, incidental census expansion, model work, outcome access, Path Risk work, execution/PnL work, or merge is authorized by this checkpoint.

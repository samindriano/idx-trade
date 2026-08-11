# PIT sector official source discovery — bounded result

Date: 2026-08-11 (Asia/Jakarta)
Status: `SOURCE_DISCOVERY_BOUNDED_COMPLETE_RAW_ATTACHMENTS_INCOMPLETE`
Branch: `data/idx-pit-sector-history-v1`

## Decision

The conceptual/source-discovery phase is complete enough to freeze the acquisition taxonomy, but the raw-source inventory is **not yet acquisition-ready** because several historical IDX attachment URLs are not publicly indexed/recovered.

Do not invent announcement numbers, dates or direct URLs to make the inventory appear complete.

## Critical methodology refinement

Two source classes that initially looked similar must be kept separate:

1. **Listed-company IDX-IC classification change announcements** are the canonical PIT event feed.
2. **Sector-index / index evaluation announcements** are reconciliation evidence only. They may react to classification changes, but they are not interchangeable with the underlying listed-company classification-change announcement.

Therefore references such as `Peng-00150/BEI.POP/06-2022`, `Peng-00156/BEI.POP/06-2023`, `Peng-00127/BEI.POP/06-2024`, and `Peng-00111/BEI.POP/06-2025` must not silently stand in for the dedicated classification-change feed.

A second important finding is that an **annual-only event log is insufficient**. PALM had an out-of-cycle/incidental IDX-IC change in September 2023, so future reconstruction must include annual routine events plus incidental events plus IPO initial classifications.

## Canonical source map recovered

### Initial baseline

- `Peng-00007/BEI.POP/01-2021`
- announced: 2021-01-13
- effective: 2021-01-25
- direct official IDX package URL recovered
- status: `READY_FOR_ACQUISITION`

### 2021 routine annual change

- `Peng-00171/BEI.POP/06-2021`
- announced: 2021-06-24
- effective: 2021-07-01
- exact reference and dates recovered from an IDX-generated issuer classification document that explicitly points back to this annual announcement
- direct raw IDX attachment URL: unresolved

### 2022 routine annual change

- BEI event date: 2022-06-24
- effective: 2022-07-01
- multiple changed issuers are independently documented
- dedicated classification-change announcement number: unresolved
- direct raw IDX attachment URL: unresolved
- `Peng-00150/BEI.POP/06-2022` is retained only as sector/index reconciliation evidence

### 2023 routine annual change

- BEI event date: 2023-06-22
- 14 listed companies were reported changed
- dedicated classification-change announcement number: unresolved
- exact effective date: left unresolved until primary evidence is acquired
- direct raw IDX attachment URL: unresolved
- `Peng-00156/BEI.POP/06-2023` is retained only as sector/index reconciliation evidence

### 2023 incidental change — PALM

- `Peng-00236/BEI.POP/09-2023`
- announced: 2023-09-29
- PALM changed from Consumer Non-Cyclicals to Financials after an incidental evaluation
- exact effective date and direct raw IDX attachment URL remain to be acquired
- this event proves annual-only reconstruction is unsafe

### 2024 routine annual change

- dedicated reference recovered as `Peng-00128/BEI.POP/06-2024`
- evidence: an official IDX-generated PANI issuer disclosure names its supporting attachment `PKIE Peng-00128.pdf`
- direct raw announcement attachment and authoritative announcement/effective dates remain unresolved
- do not substitute `Peng-00127/BEI.POP/06-2024`, which is the sector-index evaluation announcement

There is a date inconsistency that must be resolved from the raw dedicated attachment before materialization: the recovered PANI disclosure describes its classification change as effective on 2024-06-24, while the generic IDX-IC routine-evaluation rule would normally imply the first trading day of July. No assumption is authorized here.

### 2025 routine annual change

- `Peng-00110/BEI.POP/06-2025`
- announced: 2025-06-23
- effective: 2025-07-01
- changes reported for IRRA and OKAS
- direct raw IDX attachment URL: unresolved
- `Peng-00111/BEI.POP/06-2025` is retained only as sector-index reconciliation evidence

### 2026 routine annual change

- `Peng-00100/BEI.POP/06-2026`
- document date: 2026-06-24
- changes identified for ARGO, HRUM and PACK
- exact direct IDX attachment URL: unresolved
- explicit effective date remains unresolved until raw primary evidence is acquired

## Additional mandatory source classes

Even after every annual raw attachment is recovered, the history is not complete without:

1. **IPO initial classification** — every newly listed company after the applicable baseline/evaluation state needs its initial IDX-IC assignment from official listing/prospectus evidence, effective from its listing date under the frozen PIT rule.
2. **Other incidental classification changes** — the IDX announcement history must be searched for out-of-cycle changes similar to PALM 2023.

## Acquisition readiness

Current conclusion:

`NOT_READY_FOR_BULK_ACQUISITION`

Reason:

- only the January 2021 baseline has a direct official IDX attachment URL in the frozen inventory;
- several exact annual references are known but their direct IDX raw URLs are not recovered;
- 2022 and 2023 dedicated annual announcement numbers remain unresolved;
- IPO and non-annual event censuses remain required.

The public-indexed web search has reached diminishing returns. The next bounded step should be **official-portal/raw-attachment resolution**, not more model work and not inference of missing references.

## Next bounded sequence

```text
official portal / attachment lookup
        ↓
raw official acquisition + SHA-256
        ↓
inspect actual ZIP/PDF/XLSX layouts
        ↓
parser implementation
        ↓
IPO + incidental event census
        ↓
materialize PIT intervals
        ↓
coverage/conflict/leakage audit
        ↓
only then consider sector-relative model preregistration
```

## Hard boundaries

This checkpoint does not authorize:

- treating sector-index evaluation announcements as canonical classification history;
- inventing missing announcement refs or effective dates;
- current-sector backfill;
- running V3-D or another sector-relative model;
- modifying frozen V3-B;
- fresh-forward outcome access;
- Path Risk rescue;
- execution/PnL/paper/live work;
- merge to `main`.

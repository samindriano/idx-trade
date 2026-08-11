# PIT Sector Knowledge-Time Refinement

Date: 2026-08-11 (Asia/Jakarta)
Status: `RESEARCH_METHOD_REFINEMENT_RECORDED_NOT_YET_IMPLEMENTED`
Branch: `data/idx-pit-sector-history-v1`
Reviewed HEAD: `3b17126adb4b6b6dcbba127e4c2783a6520e65d3`

## Context

The multi-document official provenance contract is accepted. PALM is validly supported by canonical classification evidence plus a linked official IDX effective-date document.

Independent review identified one additional PIT-timing requirement before source-specific parsing/materialization begins.

## Refinement

A linked official effective-date document may be published **after** the effective date it proves. Such evidence should not be rejected merely because `evidence_announced_at > effective_from`.

Instead, the PIT availability time for a parsed classification event must include every decision-critical official document required to construct that event.

For an event supported by a canonical classification document plus linked effective-date evidence:

```text
pit_from = max(
    effective_from,
    canonical_announced_at,
    effective_date_evidence_announced_at,
)
```

For a single-document event, this collapses to the existing rule:

```text
pit_from = max(effective_from, canonical_announced_at)
```

## Why this matters

If a classification is legally effective on July 1 but the only explicit official evidence establishing that effective date is published on July 5, a historical model must not use the newly reconstructed classification on July 1-4. It only becomes safely knowable from July 5 under the project's PIT rule.

Rejecting all late effective-date evidence is unnecessarily strict and may block valid source recovery. Accepting the evidence while ignoring its publication time would create look-ahead leakage. The correct treatment is to preserve the event's legal effective date and separately preserve its knowledge time.

## PALM

PALM is unaffected by this refinement because its linked official effective-date evidence is dated 2023-10-02, the same date as the effective classification date. Its PIT availability therefore remains 2023-10-02.

## Required implementation before parsing/materialization

1. remove the blanket requirement that linked effective-date evidence must be announced on/before `effective_from`;
2. preserve the evidence announcement date in canonical parsed-event provenance;
3. derive event `pit_from` from the maximum of effective date and all required evidence announcement dates;
4. add adversarial tests for late official evidence;
5. keep source inventory dates explicit and provenance-linked; do not infer missing effective dates.

## Boundaries

This refinement does not authorize parser/materialization, IPO census, incidental census expansion, V3-D, V3-B modification, fresh-forward outcome access, Path Risk rescue, execution/PnL, paper/live, or main merge.

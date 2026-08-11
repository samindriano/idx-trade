# PIT Sector Raw Acquisition — Independent Review

Date: 2026-08-11 (Asia/Jakarta)
Status: `RAW_ACQUISITION_REVIEW_PASS_WITH_SOURCE_CONTRACT_REFINEMENT`
Branch: `data/idx-pit-sector-history-v1`
Reviewed source HEAD: `0183f3eb704d1cd38ad87fff5c459eafced459a0`

## Review verdict

The raw-acquisition result is accepted as a valid fail-closed data milestone.

Confirmed from the committed inventory/checkpoint/handoff:

- official IDX attachment acquisition remained outside Git;
- acquired raw files are SHA-256 pinned;
- baseline 2021, annual classification 2021, and annual classification 2025 have explicit official classification evidence plus effective dates;
- `Peng-00150/BEI.POP/06-2022` and `Peng-00156/BEI.POP/06-2023` were correctly retained as sector-index reconciliation evidence rather than silently promoted to issuer-classification history;
- PALM 2023, annual 2024, and annual 2026 have canonical classification attachments but remain blocked under the current single-document effective-date rule;
- no model, fresh-forward outcome, Path Risk, V3-B, execution, or paper/live boundary was crossed.

The fail-closed `3 ready / 5 blocked` result is therefore scientifically valid under the current source contract.

## Source-contract refinement

The review identifies one contract rule that should be refined before more source hunting:

> A canonical classification event and its effective-date evidence do not need to be contained in the same physical document, provided both pieces are official IDX evidence, hash-pinned, and explicitly linked to the same event/ticker classification change.

The canonical classification attachment remains the authority for **what classification changed**. A separate official IDX announcement/issuer disclosure may establish **when that exact change became effective** if the linkage is explicit and auditable.

This is not a relaxation to third-party evidence. It is a multi-document official-provenance contract.

Conceptually:

```text
canonical classification document
    -> what changed
    -> official IDX ref + raw SHA

linked official effective-date evidence
    -> when it became effective
    -> official IDX ref + raw SHA

both bound to same event
    -> canonical PIT event row
```

## Immediate implication — PALM 2023

PALM already has:

1. canonical classification source `Peng-00236/BEI.POP/09-2023`, proving the classification move; and
2. official IDX issuer disclosure `Peng-00016/BEI.PP1/10-2023`, explicitly stating effective **2 October 2023** and embedding/reference-linking the `Peng-00236` classification attachment.

Therefore PALM should no longer be treated as scientifically unresolved merely because the effective date is absent from the one-page canonical classification PDF. After the source schema is updated to represent separate `effective_date_evidence`, PALM is eligible to move from `DISCOVERY_REQUIRED` to `READY_FOR_ACQUISITION` without inference.

This review does not mutate the inventory status itself; the schema/test update should make the provenance relationship explicit first.

## 2024 and 2026 implication

Do **not** infer an effective date from a generic annual-July convention.

Instead, search official IDX issuer disclosures or related official announcements that explicitly reference the recovered canonical classification announcement and state the effective date. If one document establishes an event-level effective date and the linkage is unambiguous, bind it using the same multi-document provenance contract.

Any conflicting issuer-level dates must fail closed rather than be generalized to the whole annual event.

## 2022 and 2023 implication

Continue searching for the dedicated canonical issuer-classification announcements first.

If no dedicated annual package is recoverable, a fallback may be considered only after a completeness design is written: reconstruct changed sector assignments from official issuer-level disclosures plus an official census/reconciliation source that proves the full set of affected issuers. Sector-index packages alone must not silently become canonical issuer classification history.

## Scope clarification for future design

The immediate research need is a PIT-safe **sector-level** map for sector-relative alpha research. Lower IDX-IC hierarchy fields may be retained when available, but they are not required to unblock the sector-relative hypothesis.

This does not permit using incomplete sector-index membership as a substitute for sector classification history; it only prevents unnecessary blocking on subsector/industry/subindustry details when the sector code itself is official and complete.

## Next bounded action

1. implement explicit multi-document official provenance for effective-date evidence;
2. promote PALM only after that contract is represented and tested;
3. search official linked effective-date evidence for 2024 and 2026;
4. continue dedicated canonical-source resolution for 2022 and 2023;
5. stop again for review before source-specific parsing/materialization or IPO/incidental census expansion.

No V3-D/new sector model, fresh-forward outcome access, V3-B modification, Path Risk rescue, execution/PnL, paper/live, or main merge is authorized by this review.

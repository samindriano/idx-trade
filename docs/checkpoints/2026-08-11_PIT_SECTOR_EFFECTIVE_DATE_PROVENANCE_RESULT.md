# PIT Sector Effective-Date Provenance Contract Result

Date: 2026-08-11  
Branch: `data/idx-pit-sector-history-v1`  
Base review: `docs/checkpoints/2026-08-11_PIT_SECTOR_RAW_ACQUISITION_INDEPENDENT_REVIEW.md`  
Status: `MULTI_DOCUMENT_PROVENANCE_IMPLEMENTED_PALM_PROMOTED_REMAINING_SOURCES_BLOCKED`

## Implemented contract

`effective_date_evidence` is an additive optional field on a canonical source
row. When present, validation requires:

- distinct evidence `source_id` and announcement reference;
- explicit evidence `announced_at` and `effective_from`;
- official HTTPS IDX URL;
- 64-hex evidence SHA-256, positive byte count, and content type;
- linkage to the canonical source ID and announcement reference;
- linkage to the canonical raw SHA-256 when the canonical inventory pins one;
- non-empty normalized affected tickers;
- explicit classification-change and linkage statements;
- canonical top-level `effective_from` present and exactly equal to the
  evidence date.

Missing canonical dates are rejected; they are never inferred from nested
evidence. During complete acquisition, canonical and linked evidence documents
are both downloaded, SHA-verified against inventory metadata when available,
and represented in the source manifest.

## PALM promotion

PALM now passes the contract and is `READY_FOR_ACQUISITION`:

- canonical ref: `Peng-00236/BEI.POP/09-2023`;
- canonical raw SHA: `3b85b0f1bbd0cdee1ef6dc99de2b5570da892e908458303d0fbfe29bf81959d9`;
- linked effective-date ref: `Peng-00016/BEI.PP1/10-2023`;
- linked evidence SHA: `2088a9fde16bc8ac8c0da687901eb79cc7dc2124bf9c673315ebb70c1c496fb4`;
- linked ticker: `PALM`;
- explicit effective date: `2023-10-02`.

The evidence document explicitly references/embeds the canonical Peng-00236
attachment and states the effective date. No third-party source or inferred
July convention was used.

## Official discovery result

No new canonical effective-date evidence was found for 2024 or 2026:

- `Peng-00128/BEI.POP/06-2024` remains without an explicit effective date;
- `Peng-00100/BEI.POP/06-2026` remains without an explicit effective date.

No dedicated canonical annual issuer-classification attachments were recovered
for 2022 or 2023. The official `Peng-00150/06-2022` and `Peng-00156/06-2023`
packages remain sector-index reconciliation evidence only.

## Validation

- Focused PIT source tests: `14 passed`.
- Inventory CLI: `8` total canonical sources, `4` ready, `4` blocked,
  `effective_date_evidence_validated=1`, bulk acquisition still blocked.
- Full repository pytest was run after the implementation; final result is
  recorded in the result handoff and final report.

## Boundaries preserved

No parser/materialization, IPO census, incidental census expansion, V3-D,
V3-B, Path Risk, model work, fresh-forward outcome access, or main merge was
started.

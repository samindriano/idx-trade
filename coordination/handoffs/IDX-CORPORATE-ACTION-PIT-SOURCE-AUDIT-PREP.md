# IDX Corporate Action PIT — Source Audit Prep Handoff

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/corporate-action-pit-source-audit-v1`
Checkpoint: `docs/checkpoints/2026-08-13_CORPORATE_ACTION_PIT_SOURCE_AUDIT_PREP.md`

## Current repository state

- Accepted direct-IDX discovery already validated `ListingActivity/GetIssuedHistory` as an official candidate event/share-count ledger, but not a standalone PIT timing source.
- An older provider exists only on historical/non-main lineage: `src/idx_trade/providers/idx_corporate_actions.py` plus tests.
- Provider origin commits: `c8c43ac66bd3215465978ac5f39d0b72feec8a3e`, then ratio fix `14dd51796d60131ef25b318bf2258ad3dd873175`.
- Current `main` does not contain that provider.
- Existing Financial PIT direct-IDX announcement transport is reusable as a provenance/timestamp design pattern only.

## Source plan

1. IDX `GetIssuedHistory`: candidate event/share-count ledger.
2. KSEI registered-security CA history + CA schedule pages: candidate operational dates, ratios, status, revisions/cancellations.
3. IDX announcement chain: candidate publication/knowledge-time provenance and immutable attachments.

## Required bounded audit before implementation

- sample multiple years and event families;
- prove retrieval completeness/truncation behavior;
- validate KSEI ratio/date/status parsing;
- validate IDX `JumlahSaham` semantics rather than inheriting old arithmetic assumptions;
- test revision/cancellation lineage append-only;
- test deterministic KSEI↔IDX event/publication joins;
- keep unavailable fields null; do not invent a generic effective date.

## Hard boundaries

- no bulk backfill yet;
- no OHLC adjustment;
- no financial-fact parser changes;
- no model/features/outcomes;
- no Foreign Flow work; that lane is separately owned in another chat.

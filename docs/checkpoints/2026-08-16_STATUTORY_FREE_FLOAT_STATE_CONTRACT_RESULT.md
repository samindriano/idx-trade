# Statutory Free-Float Knowledge-State Contract V1 — Result

Date: 2026-08-16 Asia/Jakarta
Branch: `data/idx-statutory-free-float-state-contract-v1`
Scientific parent: `data/idx-lbre-market-anchor-reconciliation-v1@ed17ec840cf7cdcffd586f3f12bdd37b0044b004`

## Decision

`STATUTORY_FREE_FLOAT_KNOWLEDGE_STATE_CONTRACT_V1_IMPLEMENTED_READY_FOR_REVIEW`

The query-level PIT contract is implemented and tested. It resolves one
ticker/session against an explicit official IDX session set and immutable
official observations. No full historical session-state panel was
materialized.

## Frozen semantics

- Knowledge is projected only onto supplied official IDX trading sessions.
- A publication on local Asia/Jakarta date `D` becomes eligible on the first
  official session strictly after `D`.
- `as_of_date` is economic position time, never knowledge time.
- Eligible observations are replayed through the existing append-only LBRE /
  market-source lineage contract; duplicate originals, stale corrections, and
  cross-identity corrections fail closed.
- The maximum eligible economic `as_of_date` is selected. A late correction to
  an older position cannot regress a newer economic state.
- LBRE and market-wide records remain separate. Market evidence validates or
  conflicts with the same economic date and never overwrites LBRE.
- Identical shares with percentage disagreement remain denominator-eligible.
- Genuine share-count conflict is denominator-ineligible and retains both
  official source values for audit.
- Market-only exact evidence can establish a state from its own eligibility.
- Zero/non-positive official shares remain preserved as observations but are
  `INVALID_DENOMINATOR` and are not surfaced as a usable denominator.
- No stale-state cutoff is applied; knowledge/economic ages are diagnostics.

## Status contract

The resolver exposes these explicit statuses:

`USABLE_OFFICIAL_LBRE_STATE`, `USABLE_MARKET_ANCHOR_ONLY_STATE`,
`CROSS_SOURCE_SHARE_VALIDATED`, `PERCENTAGE_ONLY_DISAGREEMENT`,
`GENUINE_SHARE_COUNT_CONFLICT`, `NO_KNOWN_STATE`, and `INVALID_DENOMINATOR`.

The returned state retains source-specific record IDs, source and metadata
SHA-256 values, publication timestamps, economic dates, eligibility sessions,
reported shares/percentages, share delta, percentage-point delta, and the
later validation publication timestamp where applicable. It also exposes
knowledge age and economic-position age in official sessions and calendar
days.

## Adversarial coverage

`tests/test_statutory_free_float_state.py` contains 15 tests covering:

- publication on a trading day and over a weekend;
- append-only correction timing;
- late correction to an older economic position;
- newer snapshot followed by an older-period correction;
- old conflict discovered after a newer snapshot exists;
- LBRE-first then market validation/conflict;
- market-first then LBRE agreement/conflict;
- percentage-only disagreement;
- no observation;
- zero denominator;
- duplicate/ambiguous lineage input;
- timezone-naive timestamps;
- duplicate official sessions;
- provenance and age diagnostics.

## Validation

- Focused state + statutory parent suites: `33 passed`.
- Full pytest: `87 collected; 86 passed; 1 failed`.
- The failure is the existing unrelated storage expectation:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.
  It expects one conflict while current storage independently reports
  `raw_close` and `vendor_adj_close` conflicts. No storage change was made.
- `git diff --check`: pending final staged validation.

## Boundaries respected

No provider/network call, historical panel materialization, synthetic grid,
forward-fill, holder/HSC/>=1% reconstruction, effective supply, Foreign Flow
V2 modification, feature/model work, O2/counter work, or outcome access was
performed.

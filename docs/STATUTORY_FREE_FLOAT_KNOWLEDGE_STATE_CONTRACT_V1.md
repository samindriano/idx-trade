# Statutory Free-Float Knowledge-State Contract V1

Status: `FROZEN_FOR_REVIEW`
Date: 2026-08-16 Asia/Jakarta
Scientific parent: `data/idx-lbre-market-anchor-reconciliation-v1@ed17ec840cf7cdcffd586f3f12bdd37b0044b004`

## Purpose and boundary

This contract resolves what official statutory free-float evidence was
knowable for one ticker on one official IDX trading session. It is a query-level
foundation only. It does not materialize a historical session panel, create a
ticker-month grid, forward-fill, reconstruct free float from holders/HSC/>=1%,
calculate effective supply, integrate Foreign Flow, or access models/outcomes.

The input observations are the existing immutable official LBRE and market-wide
records represented by `HistoricalFreeFloatObservation`. Their record IDs,
source hashes, metadata hashes, publication timestamps, and source families are
preserved. No source is silently preferred over another.

## Session knowledge time

The caller supplies an explicit set of official IDX trading-session dates.
Calendar days are never substituted for missing exchange sessions. Publication
timestamps must be timezone-aware. Their local date is computed in
`Asia/Jakarta`.

For an observation published on local date `D`, the observation first becomes
eligible on the first supplied official session with date strictly greater than
`D`. Therefore publication on a trading day is not usable on that same session;
publication over a weekend becomes usable on the next official session.
`as_of_date` is an economic position date only and is never used as knowledge
time.

## Lineage and economic-state selection

Before resolution, eligible observations are replayed through the existing
append-only lineage contract. A correction is usable only after its own
publication eligibility and only when it deterministically supersedes the
currently active record for the same ticker, economic position, and source
family. Duplicate originals, duplicate record IDs, stale corrections, and
cross-identity corrections fail closed.

For a query `(ticker, session_date)`:

1. keep only observations eligible by that official session;
2. replay the remaining observations independently by source family;
3. choose the maximum available economic `as_of_date` across current LBRE and
   market-wide observations;
4. compare source observations only when they share that selected economic
   date.

A late correction to an older economic position therefore cannot regress a
   newer state. If a newer economic snapshot exists, an old-period conflict
   discovered later does not poison that newer state.

## Cross-source state and denominator semantics

The resolver returns one explicit `StatutoryFreeFloatKnowledgeState` with
source-specific LBRE and market fields. `free_float_shares` is populated only
when the surfaced denominator is unambiguous and strictly positive. Source
reported zero values remain in their source-specific observation fields but are
not denominator-eligible.

Statuses are:

- `USABLE_OFFICIAL_LBRE_STATE`: only LBRE is available for the selected
  economic position and its shares are positive.
- `USABLE_MARKET_ANCHOR_ONLY_STATE`: only market-wide evidence is available and
  its shares are positive.
- `CROSS_SOURCE_SHARE_VALIDATED`: both sources cover the same economic date,
  shares are identical, and percentages are within the existing 0.01 pp
  diagnostic tolerance.
- `PERCENTAGE_ONLY_DISAGREEMENT`: shares are identical but reported
  percentages differ beyond tolerance; the denominator remains eligible.
- `GENUINE_SHARE_COUNT_CONFLICT`: same-date source share counts differ; no
  denominator is surfaced and both official values remain available for audit.
- `NO_KNOWN_STATE`: no eligible observation exists for the query.
- `INVALID_DENOMINATOR`: a single-source or share-validated state has a
  non-positive denominator. The official source value remains preserved.

Market evidence validates or conflicts with LBRE at the same economic date; it
never overwrites LBRE. Market-only exact evidence can establish its own state
from its own eligibility session.

The chronology is source-symmetric. For the selected economic position, the
state exposes `first_known_published_at` and
`first_known_eligible_from_session` for the earliest official evidence from
either source. It separately exposes `status_effective_published_at` and
`status_effective_eligible_from_session` for the later evidence that makes the
cross-source validation or conflict status knowable. A later source therefore
changes validation status, not the original first-known time. The legacy
`source_published_at` and `eligible_from_session` fields are compatibility
aliases for the first-known timeline.

When both sources report identical shares, the denominator remains eligible.
`free_float_pct` is canonical only for a single source or exactly identical
cross-source percentages. Any non-identical percentages, including values
within the diagnostic tolerance, leave `free_float_pct` unset while retaining
both source-specific percentages and their exact delta.

## Provenance and diagnostic ages

The state exposes source record IDs, attachment SHA-256 values, metadata
SHA-256 values, source-specific publication/as-of dates, and source-specific
eligibility sessions. It also exposes:

- `source_as_of_date`;
- `first_known_source_families` and `first_known_record_ids`;
- `first_known_published_at` and `first_known_eligible_from_session`;
- `status_effective_published_at` and `status_effective_eligible_from_session`;
- `source_published_at`;
- `eligible_from_session`;
- `knowledge_age_sessions`: zero on the first eligible session, then elapsed
  official sessions since eligibility;
- `knowledge_age_days`: query local session date minus the local publication
  date;
- `economic_position_age_sessions`: query session index minus the first
  official session on/after the economic as-of date;
- `economic_position_age_days`: query local session date minus economic as-of
  date.

When both sources are present, `validation_published_at` records the same
later source publication represented by the status-effective timeline. The
corresponding `status_age_sessions` and `status_age_days` expose age from that
status-effective evidence. No V1 stale-state cutoff is applied; these age
fields are diagnostics for a later coverage/policy decision.

## Implementation and tests

Implementation: `src/idx_trade/statutory_free_float_state.py`
Focused adversarial tests: `tests/test_statutory_free_float_state.py`

The test contract covers trading-day and weekend publication, correction
eligibility, late old-period corrections, newer-snapshot protection, LBRE and
market source ordering, percentage-only disagreement, genuine share conflict,
no state, zero denominator, duplicate/ambiguous lineage, duplicate sessions,
timezone-naive rejection, provenance preservation, and diagnostic ages.

No historical session-state materialization is authorized by this document.

# Statutory Free-Float Knowledge-State Contract V1 — Remediation Addendum

Status: `REVIEW`
Date: 2026-08-16 Asia/Jakarta
Parent implementation: `data/idx-statutory-free-float-state-contract-v1@8e0892f6261b4553965949150df95d689ead1376`

This addendum records the contract-correctness remediation. It does not change
source artifacts, parser behavior, monthly history, reconciliation inputs, or
the authorization boundary against historical session-panel materialization.

## Symmetric cross-source chronology

For the selected economic `source_as_of_date`, the resolver now exposes two
independent timelines:

- `first_known_*`: the earliest official evidence among the selected LBRE and
  market-wide observations, plus its first eligible official session;
- `status_effective_*`: the later evidence time/session at which the
  cross-source validation or conflict status became knowable.

The backward-compatible `source_published_at` and `eligible_from_session`
fields are aliases for the first-known timeline. They are not an implicit LBRE
publication origin. `validation_published_at` remains the later source time
when both sources are present.

Consequently, market-first/issuer-later and issuer-first/market-later cases
are symmetric: later evidence changes validation status, never the original
knowledge time of the denominator.

## Canonical percentage rule

Source-specific percentages remain available as
`lbre_free_float_pct` and `market_free_float_pct`, with their exact
percentage-point delta. A canonical `free_float_pct` is exposed only when:

- one official source is present and its positive denominator is usable; or
- both official sources report exactly the same percentage and the identical
  share count is denominator-eligible.

Identical shares with any non-identical reported percentages, including a
difference within the 0.01 percentage-point diagnostic tolerance, expose the
shares but set canonical `free_float_pct=None`. No percentage is averaged,
recalculated, or silently preferred.

## Required preserved invariants

The remediation preserves strict next-official-session eligibility, maximum
economic `as_of_date` precedence, append-only correction replay, late
old-period correction protection, positive-denominator requirements, market-only
usable states, genuine share-count conflict fail-closed behavior, and exact
source provenance.

Focused adversarial coverage includes both source-order permutations for
agreement and conflict, percentage-only disagreement (including the
within-tolerance case), exact-percentage agreement, single-source percentage
preservation, and protection of a newer economic snapshot from later
old-period evidence.


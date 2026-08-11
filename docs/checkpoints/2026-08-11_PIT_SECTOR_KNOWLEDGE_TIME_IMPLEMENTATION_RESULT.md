# PIT Sector Knowledge-Time Refinement — Implementation Result

Date: 2026-08-11 (Asia/Jakarta)
Status: `PIT_KNOWLEDGE_TIME_REFINEMENT_IMPLEMENTED`
Branch: `data/idx-pit-sector-history-v1`

## Reason

The prior multi-document effective-date contract rejected supporting official evidence whenever its publication date was later than the effective date. That was unnecessarily strict and could also encourage the wrong PIT interpretation.

A later official document may validly establish that an event became effective on an earlier date. The historical fact can be accepted, but it must not become usable in a backtest before the supporting evidence itself was knowable.

## Implemented rule

For a canonical classification event with linked official effective-date evidence:

```text
knowledge_at = max(
  effective_from,
  canonical announced_at,
  supporting evidence announced_at
)
```

The parsed event layer then uses:

```text
pit_from = max(effective_from, announced_at, knowledge_at)
```

When no later decision-critical supporting evidence is needed, `knowledge_at` defaults to canonical `announced_at` and historical behavior is unchanged.

## Contract changes

`validate_effective_date_evidence` now:

- permits official supporting evidence to be announced after the event's effective date;
- still requires the canonical top-level `effective_from` to be explicit and exactly equal to the supporting evidence's stated effective date;
- still requires official IDX HTTPS provenance, SHA-256, canonical source/ref/hash linkage, affected ticker(s), and linkage statements;
- derives and returns `knowledge_at` from the latest decision-critical date;
- does not infer a missing effective date.

`acquire_official_sources` now records supporting-evidence `announced_at` and derived `knowledge_at` in the acquisition manifest.

`normalise_sector_events` now accepts an optional explicit `knowledge_at` field. If absent it defaults to `announced_at`; if present it participates in the PIT boundary and cannot be null.

`attach_sector_asof` exposes `knowledge_at` in joined output so the temporal decision boundary remains auditable.

## Ordering safety guard

Allowing delayed evidence introduces a second edge case: an older classification could theoretically become knowable only after a newer classification is already known. A simple as-of join on `pit_from` would then risk letting the older event overwrite the newer effective state.

Until a dedicated two-dimensional state resolver is explicitly designed, the current implementation fails closed when the per-ticker `pit_from` sequence moves backward relative to increasing `effective_from`.

Example that is rejected:

```text
older event: effective 2024-07-01, knowledge 2024-08-01
newer event: effective 2024-07-15, knowledge 2024-07-15
```

This guard preserves correctness of the current interval/as-of implementation instead of silently resolving an ambiguous event topology.

## Adversarial coverage

Tests cover both knowledge-time cases.

Delayed evidence is accepted and time-gated:

```text
effective_from                 2024-07-01
canonical announced_at         2024-06-24
supporting evidence announced  2024-07-05

PIT usable                     2024-07-05
```

The event is deliberately invisible on 1–4 July and becomes available only on 5 July.

A reversed knowledge/effective ordering across two events is rejected fail-closed rather than allowed to overwrite a newer classification.

Existing PALM treatment remains unchanged because its canonical effective date and linked official evidence publication date are both 2 October 2023.

## Validation

GitHub Actions on the refined branch completed successfully:

- full repository pytest: `488 passed`;
- PIT source test file now contains `17` focused tests, including delayed-evidence and non-monotonic-order adversarial cases;
- no new test failure was introduced.

The workflow still reports existing repository-wide warning noise; the knowledge-time change itself is green.

## Inventory implication

This refinement does not promote any new source by itself. The canonical inventory remains:

- `4` ready;
- `4` blocked: annual 2022, annual 2023, annual 2024, annual 2026.

It changes how future supporting official evidence is admitted and time-gated once found.

## Boundaries

No source-specific parser/materialization, IPO census, incidental census expansion, sector-relative model, V3-B modification, fresh-forward realized outcome access, Path Risk rescue, execution/PnL, paper/live work, or main merge is authorized or performed by this refinement.

# INC-001 CA-Aware Feature-Basis Remediation V1 — R3.2 Certification Hardening

Date: 2026-08-28 Asia/Jakarta
Branch: `data/ca-aware-feature-basis-remediation-v1`
Scope: narrow outcome-blind R3.2 fail-closed certification hardening only.

## Boundaries

This checkpoint does not run Phase-E, call providers, access outcomes or
targets, fit/refit/score models, mutate counters, or rewrite canonical
historical data. No production execution or backfill was performed. The
existing R3 and R3.1 artifact roots remain immutable.

No new R3.2 population/dependency artifact was generated: the hardened paths
only make certification stricter, and the current pinned production audit
result remains FAIL/UNKNOWN. The R3.1 artifact and deterministic rerun remain
the evidence for the current 26-row census.

## Transition lower-bound provenance

`classify_event_scope()` continues to treat a candidate/source date as event
evidence only. `candidate_date > closure_end` remains
`UNKNOWN_UNRESOLVED_AFTER_CLOSURE` unless a source-specific transition lower
bound is certified and is itself after `closure_end`.

Certification now requires all of the following:

- explicit certified state;
- an accepted source-bound status;
- non-empty source reference;
- non-empty, valid 64-hex evidence SHA-256;
- valid lower-bound date.

An explicit lower-bound source-contract identifier is carried when supplied;
the minimum contract remains source reference plus evidence hash. Empty or
malformed evidence SHA, missing source reference, status/boolean alone, and
malformed lower-bound dates remain unresolved.

The current R3.1 26-row census is unchanged: `0` outside classifications and
`5` `UNKNOWN_UNRESOLVED_AFTER_CLOSURE`, with the remaining counts `10` outside
ticker, `3` unresolved before closure, and `8` unresolved in closure. No new
`OUTSIDE_DEPENDENCY_AFTER_CLOSURE` row is admitted by R3.2.

## Global population certification

`global_ca_population_gate()` no longer has a count-equality pass condition
and cannot pass from `scope_evidence` booleans such as
`source_family_certified=True`, `date_level_attestation=True`, or
`structural_event_complete=True` without evidence provenance.

The authoritative pass path is:

```text
evidence-rich family rows
  -> prepare_family_coverage()
  -> combine_family_coverage() using the exact frozen structural family set
  -> full application/closure identity certification
  -> source/ref/hash-bound temporal as-of certification
  -> PASS
```

The gate requires fit identities/tickers to be contained in application scope,
application identities/tickers to be contained in closure scope, every full
expanded application/closure identity to have all frozen family evidence, and
every such identity to have valid temporal/as-of provenance. Family source
contracts, source references, evidence hashes, conflicts, and deterministic
composite evidence hashes are validated before PASS. Identity ticker sets must
also match their declared scope sets, so an omitted expanded application
identity cannot be hidden by a correct ticker count.

The synthetic acceptance architecture remains valid:

```text
fit population        = 629
cross-sectional app   = 716
dependency closure    = 716
```

It can PASS only with complete provenance-bound evidence for all 716 expanded
identities. Fit-only 629 evidence, missing frozen families, conflicting family
evidence, missing/malformed family hashes, naked date/as-of booleans, and
partial identity scope all fail closed.

## Required red-team regressions

The R3.2 regression set proves:

```text
A 629/716/716 + complete family and temporal provenance       PASS
B same identities + naked booleans/no refs or hashes         FAIL
C one frozen structural family missing                       FAIL
D missing or malformed family evidence SHA                   FAIL
E missing date/as-of provenance                               FAIL
F conflicting family evidence                                FAIL
G 629-only evidence cannot certify expanded 716 scope        FAIL
H certified lower bound with empty SHA cannot classify OUTSIDE FAIL
```

## Scientific verdict unchanged

```text
DATA_ADMISSION       = FAIL
RESEARCH_ADMISSION   = FAIL
MODEL_PROMOTION      = NOT_EVALUATED
HISTORICAL_APPLICATION = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED     = FALSE
COUNTER_ACTION       = NONE
```

## Validation

Pre-push local validation for this checkpoint:

```text
Focused R3.2 reconciliation tests: 31 passed
All CA/integrity tests: 110 passed
Full pytest: 349 passed
py_compile: PASS
git diff --check: PASS
Exact-head GitHub Actions run 33131395428 at bcfd2ea4: 349 passed, 5 warnings
```

The exact-head run is green. Its five warnings are the existing two NumPy
timedelta deprecations and three Node/action deprecation annotations; no test
failed. The final documentation update is recorded in the companion handoff.
PR #108 remains unmerged.

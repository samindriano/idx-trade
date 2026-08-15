# Statutory Free-Float Knowledge-State Contract V1 Remediation Result

Date: 2026-08-16 Asia/Jakarta  
Branch: `data/idx-statutory-free-float-state-contract-v1-remediation`  
Scientific parent: `data/idx-statutory-free-float-state-contract-v1@8e0892f6261b4553965949150df95d689ead1376`

## Scope

This was an independent contract-correctness remediation only. No provider or
network calls, source-artifact changes, parser/monthly-history/reconciliation
changes, historical session-panel materialization, effective-supply work,
Foreign Flow work, model/outcome access, or O2 changes were performed.

## Remediations

The resolver now keeps separate first-known and cross-source
status-effective publication/session timelines. The first-known timeline is
the earliest official evidence for the selected economic position regardless
of source family; the status-effective timeline is the later evidence that
makes cross-source validation or conflict knowable. Existing
`source_published_at` / `eligible_from_session` aliases now expose first-known
time for compatibility.

Canonical percentage selection is now fail-closed for any non-identical
cross-source percentages. Identical shares remain denominator-eligible, and
source-specific percentages plus their delta remain available. A canonical
percentage is exposed only for a single source or exactly identical
cross-source percentages.

## Validation

Focused command:

```text
python -m pytest tests/test_statutory_free_float_state.py -q
```

Result after remediation: `18 passed, 0 failed`.

The focused tests cover strict publication timing, weekend timing, correction
lineage, late old-period protection, both source-order permutations for
agreement and conflict, first-known versus status-effective chronology,
percentage-only disagreement beyond and within tolerance, exact percentage
agreement, single-source percentage preservation, no state, invalid
denominator, ambiguous lineage, duplicate sessions, timezone rejection, and
age diagnostics.

The full-repository result is recorded in the final handoff after execution;
the known unrelated storage revision-mode test remains separately reported if
it persists.

## Decision

`REVIEW` — remediation is complete and ready for independent ChatGPT review.
Historical session-state materialization remains explicitly not authorized.


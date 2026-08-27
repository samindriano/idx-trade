# INC-001 CA-Aware Feature-Basis Remediation V1 — R3.1 Red-Team Correction

Date: 2026-08-28 Asia/Jakarta  
Branch: `data/ca-aware-feature-basis-remediation-v1`  
Scope: narrow R3.1 correction for event-scope fail-open, expanded-population gate dead-end, support-lineage attribution, and validation wording.

## Boundaries

This checkpoint is outcome-blind and offline. It does not run Phase-E,
providers, outcomes, model fit/refit/scoring, counter mutation, or canonical
historical rewrites. The existing R3 root remains immutable. R3.1 writes only
to the new artifact roots below.

## Event-scope correction

`classify_event_scope()` now treats a candidate/source date as evidence only.
`candidate_date > closure_end` produces
`UNKNOWN_UNRESOLVED_AFTER_CLOSURE` unless source-specific evidence carries a
certified transition lower bound with an attested source reference and that
lower bound is itself after `closure_end`.

The pinned 26-row census changed as follows:

| Classification | R3 before | R3.1 after |
|---|---:|---:|
| `OUTSIDE_DEPENDENCY_AFTER_CLOSURE` | 5 | 0 |
| `UNKNOWN_UNRESOLVED_AFTER_CLOSURE` | 0 | 5 |
| `OUTSIDE_DEPENDENCY_TICKER` | 10 | 10 |
| `UNRESOLVED_CANDIDATE_BEFORE_CLOSURE` | 3 | 3 |
| `UNRESOLVED_CANDIDATE_IN_CLOSURE` | 8 | 8 |

The five affected source identities are:

```text
IDX_GET_ISSUED_HISTORY|MLPT|STOCK_SPLIT|2026-07-21|82680
KSEI_REGISTERED_SECURITY|MLPT|MANDATORY_CONVERSION|2026-07-23|
KSEI_REGISTERED_SECURITY|RAJA|MANDATORY_CONVERSION|2026-07-20|
IDX_GET_ISSUED_HISTORY|SCMA|CAPITAL_RESTRUCTURING|2026-08-10|82840
IDX_GET_ISSUED_HISTORY|SINI|RIGHTS_HMETD|2026-07-24|82732
```

No current census row has a certified transition lower bound, so none is
classified outside solely from its candidate date.

## Expanded population gate

`global_ca_population_gate()` no longer rejects the valid expanded scope by
count equality. Its pass path requires identity/set containment and complete
evidence for the full expanded scope:

```text
final-fit identities/tickers ⊆ application identities/tickers
application identities/tickers ⊆ dependency-closure identities/tickers
every application/closure identity is source-family certified
every application/closure identity has valid date-level attestation
```

The regression suite proves that `629 / 716 / 716` can pass when all expanded
identity evidence is certified, while fit-only evidence, missing identities,
or incomplete date attestation fail closed. The current audit remains blocked
because its pinned KSEI data is not date-level attested and structural CA
coverage is not certified; the new gate no longer reports expanded scope as a
failure merely because its counts differ.

## Support-lineage mechanism

The accepted identity arithmetic is unchanged:

| Support | Old | Current | Common | `OLD_ONLY` | Current-only |
|---|---:|---:|---:|---:|---:|
| H5 | 241,487 | 239,648 | 239,648 | 1,839 | 0 |
| H10 | 239,836 | 237,976 | 237,976 | 1,860 | 0 |
| Union | 241,724 | 240,344 | 240,344 | 1,380 | 0 |

All 1,380 UNION `OLD_ONLY` rows are classified as
`CLEAN_SECURITY_MASTER_ADMISSION_PLUS_CA80_DATE_GATE_FLIP`. The pinned
identity-only evidence proves that each affected date has the clean `FREN`
`PRIMARY_ADD`, a corresponding H5/H10 drop, and a clean CA80 eligibility
value below the inclusive `0.80` gate. The global Stage-C decision remains
`V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION`.

The individual numerator/support attribution for each row is explicitly
`UNKNOWN`; no protected outcome or target artifact was inspected. The old
56,602-row overlay remains not applicable/unproven on current Phase-B support.

Lineage evidence hashes:

```text
old_vs_clean_primary_identity_delta.csv = f07bfec5d89443e05512984364831034b1571c7337e1257e685e6bf71e58a240
old_vs_clean_support_delta.csv          = ae13c763515ee86bf8934d6883dd089ae3aae5504ba317f8d951ffdcbf2f5862
clean_ca80_support_per_date.csv         = b36114623df7dc9475fd5227f877f9cae887a28f17b31448f28e26d443715f79
```

## Immutable R3.1 artifacts

Primary root:
`D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260828-r3_1-final`

R3.1 manifest SHA-256:
`9075b707db70cf7e2a6fce4b504bfdf8c16369b9de75420f90d9808f1b994c2b`

R3.1 summary SHA-256:
`e370b33e39627b1024d1cae9655684e60b2975d456df717e8a13accd5bc69cbb`

The deterministic rerun root is:
`D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260828-r3_1-final-rerun`

Both roots are new and do not overwrite the R3 root. The manifest records all
10 output hashes, the prior R3 manifest/scope hashes, the before/after scope
counts, the five affected identities, and the 1,380-row mechanism inventory.

## Validation and guardrails

```text
Focused R3.1 regressions: 22 passed
py_compile: PASS
git diff --check: PASS
Exact-head GitHub Actions baseline 33089485270: 334 passed, 5 warnings
Phase-E: FALSE
providers: FALSE
outcomes: FALSE
target_values_accessed: FALSE
model_fit: FALSE
model_scoring: FALSE
counter_mutated: FALSE
canonical_artifacts_mutated: FALSE
historical_feature_recompute: FALSE
```

Full pytest and the post-push exact-head run are recorded in the companion
R3.1 handoff after completion. PR #108 is not merged by this work.

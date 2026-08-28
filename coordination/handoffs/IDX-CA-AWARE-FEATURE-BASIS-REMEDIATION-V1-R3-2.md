# Handoff

from: MAIN / Codex
to: ChatGPT review
task_id: IDX-CA-AWARE-FEATURE-BASIS-REMEDIATION-V1-R3-2
branch: `data/ca-aware-feature-basis-remediation-v1`

## Scope

Narrow outcome-blind R3.2 certification hardening only. Transition lower-bound
certification now requires explicit certified state, accepted source-bound
status, source reference, valid non-empty 64-hex evidence SHA-256, and valid
lower-bound date. The global population gate has one evidence-rich family and
temporal certification path and cannot pass from naked caller booleans.

No Phase-E, provider, outcome/target, model fit/refit/scoring, counter
mutation, canonical historical rewrite, production execution, or backfill was
performed. PR #108/#103 was not merged.

## Results

- Empty/malformed transition evidence SHA, missing source reference, and
  boolean/status-only lower-bound claims remain `UNKNOWN`; only valid
  source-bound certification can produce `OUTSIDE_DEPENDENCY_AFTER_CLOSURE`.
- The current R3.1 26-row census remains `0` outside-after-closure and `5`
  unresolved-after-closure; no new outside classification was introduced.
- `global_ca_population_gate()` accepts the valid `629` fit / `716`
  application / `716` closure architecture only when the full expanded
  identity scope has exact-family, source/ref/hash-bound evidence and temporal
  as-of evidence.
- The gate rejects naked booleans, partial 629-only coverage, missing or
  conflicting frozen families, malformed/missing hashes, and unproven temporal
  attestation. Application identity ticker-set mismatches also fail closed.
- Current scientific verdict is unchanged: data/research admission FAIL,
  model promotion NOT_EVALUATED, historical application blocked by
  `PHASE_E_NOT_RUN`, refit unauthorized, counter action NONE.

## Artifacts

No R3.2 artifact root was generated because the hardened logic does not change
the current FAIL/UNKNOWN production result. The following pre-existing roots
remain immutable and were not overwritten:

```text
R3 root:   D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260827-v3-final
R3.1 root: D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260828-r3_1-final
```

The R3.1 manifest and summary remain the evidence for the current census and
the R3.1 deterministic rerun remains unchanged.

## Validation

- Focused R3.2 reconciliation tests: **31 passed**.
- All CA/integrity tests: **110 passed**.
- Full pytest: **349 passed**, exit 0.
- `py_compile`: pending final local check.
- `git diff --check`: pending final local check.
- Exact-head GitHub Actions: pending post-push run.

## Review boundary

Review the R3.2 source/test diff and the new checkpoint. Do not run Phase-E,
access outcomes/providers, fit/refit/score, mutate counters, regenerate
expensive population/dependency artifacts, rewrite canonical historical data,
or merge PR #108/#103 as part of this handoff.

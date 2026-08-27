# INC-001 CA-Aware Feature-Basis Remediation V1 — A-D Audit R2

Date: 2026-08-27 Asia/Jakarta  
Branch: `data/ca-aware-feature-basis-remediation-v1`

## Correction

R2 closes an audit-scope omission in the first local A-D report: the runner
now verifies the accepted clean panel SHA and reads only its `date` column to
pin the full historical feature-observation interval. The first R1 output was
not overwritten and remains available for audit history.

The full clean panel interval is **2021-04-29 through 2026-07-31**, covering
981,940 rows. The exact final-fit support union remains **2022-02-11 through
2026-07-17**, with 240,344 deduplicated identities and 629 tickers. This
distinction matters: CA temporal coverage must cover the full feature
observation interval, not only rows that survived the final-fit support gate.

The KSEI snapshot still has no `coverage_start_session`,
`coverage_end_session`, `coverage_observed_at`, or per-session no-event
attestation. Its retrieval interval remains
`2026-08-17T16:28:38.283516Z` — `2026-08-17T17:57:30.274512Z`; this is not a
historical publication or as-of timestamp.

## Result

The correction does not change the scientific decision:

```text
EXACT_FINAL_FIT_POPULATION = PASS_IDENTITY_RECONCILED
KSEI_POPULATION_COVERAGE = FAIL_629_VS_610
TEMPORAL_COVERAGE = UNKNOWN_NO_PER_SESSION_AS_OF_ATTESTATION
STRUCTURAL_CA_FAMILY_COVERAGE = FAIL_PARTIAL_OR_CONFLICTING_FAMILY_EVIDENCE
TRANSITION_SEMANTICS = FAIL_OR_UNKNOWN_ALL_STRICT_EVENTS_UNRESOLVED
BACKWARD_CA_FEATURE_WINDOW_RISK = PRESENT_NO_GLOBAL_CA_AWARE_ADMISSION
HISTORICAL_APPLICATION = BLOCKED_PHASE_E_NOT_RUN
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
MODEL_PROMOTION = NOT_EVALUATED
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

The frozen observed-row dependency geometry remains:

```text
close_return_5:   t-5..t   -> 5 direct post-transition rows
ATR14:            t-14..t  -> 14
close_return_20:  t-20..t  -> 20
rolling20:        t-19..t  -> 20
rolling60:        t-59..t  -> 59
```

No date was inferred from a source event field, no source family was merged,
and no Phase-E feature/rank/context recomputation was attempted.

## R2 external artifacts

Root:
`D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260827-v2`

| Artifact | SHA-256 |
|---|---|
| `MANIFEST.json` | `0a83472bf04cdd8d7d62cfd0e59d8323ba46065f7079d3298059e7f1e60e6fb7` |
| `summary.json` | `7cf6717d3317845d65a52b61df3892a2c29d8c3357fccd54c1680c9cad34c4a0` |
| `population_reconciliation.csv` | `3fad40646a04cbf3173d46bfe82537f027b594a20c3c29f4d41e7c0162f124db` |
| `structural_ca_event_ledger.csv` | `426f82fdbe4d8cbcc2a6c00bef2676a758c7c48fb22463f80c9b986bcc42e0f5` |
| `ca_family_coverage.csv` | `b0f2e0f18ab146526f78c25baff61eb9e6a79d56af01143812ba03ff655574d8` |
| `temporal_coverage.csv` | `0d9b43a0b5684553dd0d6ab25343ec2f9a5182fcfe605203bdbf64ac19f16e94` |
| `model_population_classification.csv` | `6203ad936c2630cc7c84bd8a824a2ca31d7f4f31de45995f9bfb6ecbe82ce1d6` |

The same R2 inputs were run into a separate fresh `-rerun` root. All seven
output hashes matched (`0` mismatches), including the newly added clean-panel
interval evidence.

## Validation

The focused reconciliation, CA-feature, V4-contract, and research-integrity
tests passed: **84 passed**. The full repository suite passed: **323 passed**
with a fresh external pytest base directory. The reconciliation runner also
passed `py_compile`, and `git diff --check` passed. No source/runtime
provider, outcome, model, counter, or Phase-E operation was run.

## Guardrails

```text
outcome_blind = true
target_values_accessed = false
outcomes_accessed = false
provider_calls = false
model_fit = false
model_scoring = false
historical_feature_recompute = false
phase_e_run = false
counter_mutated = false
canonical_artifacts_mutated = false
```

This is an audit-only R2 correction and is ready for ChatGPT review. No
historical application, refit, promotion, or counter action is authorized.

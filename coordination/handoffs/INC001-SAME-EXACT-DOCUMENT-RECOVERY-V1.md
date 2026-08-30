# Handoff: INC-001 SAME exact-document recovery V1

Status: `REVIEW`

Branch: `data/ca-aware-feature-basis-remediation-v1`

Implementation head: `0985162074ea1c922d378e28bedfbc15768e02c6`

PR #108: OPEN/DRAFT/unmerged. PR #103: unmerged.

## Decision

`SAME` was recovered exactly from the already-known official KSEI PDF. The
event-specific transition is now source-bound and accepted, but this does not
authorize the remaining RIGHTS population. The source-path decision remains
`HOLD_FOR_ALTERNATE_SOURCE_PATH`.

No index lookup was repeated. No SGER/PACK request was made. Exactly one PDF
retrieval was attempted, with no retry or alternate URL.

## Exact result

```text
SAME_PDF_REQUEST_RESULT = HTTP_200_VALID_PDF
SAME_DOCUMENT_REFERENCE = KSEI-3077/JKU/0221
SAME_DOCUMENT_SHA256 = 1281dc227ca94d417f074cff17396ffbdfab4b464669ff2251f77c3b247dc0c0
SAME_EXPLICIT_EX_SEMANTIC = TRUE
SAME_ACCEPTED_EX_DATE = 2021-03-02
SAME_FINAL_CLASSIFICATION = RESOLVED_EXACT
```

The explicit source wording is semantically equivalent to
`Tanggal Ex di Pasar Regular dan Pasar Negosiasi`. Candidate, cum, record,
distribution, publication, exercise, and next-session dates were not used as
the transition date.

## Linkage and reconciliation result

```text
PRIOR_PROVEN_LINKAGES = 27
RECOMPUTED_PROVEN_LINKAGES = 27
NEW_PROVEN_LINKAGES = 0
REMOVED_OR_CONFLICTING = 0

ECONOMIC_EVENTS = 387 -> 387
RESOLVED = 159 -> 160
UNRESOLVED = 182 -> 181
NON_BASIS = 46
RIGHTS_HMETD_UNRESOLVED = 69 -> 68
```

The exact evidence resolves the existing SAME economic event; it does not add
a source-pair linkage. The normal reconciler used immutable V13 inputs and
did not modify the V13 root or canonical historical data.

## Artifact pins

```text
RECOVERY_ROOT = D:\Documents\Project\idx-ca-same-exact-document-recovery-20260830-v2
RECOVERY_MANIFEST_SHA256 = a08f27a6cf20730b824c87b138e84e6e17f851769b565d2c357ff8d1e7bd3353

SUCCESSOR_RECONCILIATION_ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v14-same-exact
SUCCESSOR_RECONCILIATION_MANIFEST_SHA256 = c095c00c31691c07cbf4d50c447abafde9b00db0e93f8184ea6e9a83b4a1990b
DETERMINISTIC_RERUN_ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v14-same-exact-rerun
DETERMINISTIC_RERUN_MANIFEST_SHA256 = aa482653a0e0c037e18397a3108b2dd331c9aeb4b7f9ff8e7d8d625060a3d548
DETERMINISTIC_COMPARISON = PASS (13/13 non-manifest files identical)
```

## Validation and guardrails

```text
FOCUSED_RIGHTS_AND_RECONCILIATION_TESTS = 23 passed
CA_INTEGRITY_SUITE = 131 passed (13 modules)
FULL_PYTEST = 392 passed
COMPILEALL = PASS
GIT_DIFF_CHECK = PASS
ARTIFACT_HASH_VALIDATION = PASS (3 roots, zero mismatches)
DETERMINISTIC_RECONCILIATION = PASS (13/13 non-manifest files identical)
EXACT_HEAD_CI = PASS, run 33305713431 @ 89c3a36c; 392 passed, 5 pytest warnings
```

The known non-blocking GitHub Actions Node.js 20 deprecation annotation must be
reported separately from test results. GitHub's separate annotation was the
Node.js 20 deprecation notice for `actions/checkout@v4` and
`actions/setup-python@v5`; it was not a test failure.

```text
RIGHTS_ARCHIVE_ROUTING_CONTRACT_VERDICT = RIGHTS_ARCHIVE_ROUTING_CONTRACT_PARTIAL
RIGHTS_INDEX_SOURCE_CONTRACT_VERDICT = RIGHTS_INDEX_LIVE_CONTRACT_CONDITIONALLY_REPEATABLE
FULL_RIGHTS_ACQUISITION_RECOMMENDATION = HOLD_FOR_ALTERNATE_SOURCE_PATH

IDX_HISTORICAL_NEGATIVE_AUTHORITY = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN

DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
MODEL_PROMOTION = NOT_EVALUATED
HISTORICAL_APPLICATION = BLOCKED_PHASE_E_NOT_RUN
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

Await ChatGPT review. Do not acquire more RIGHTS events, run Phase-E, access
outcomes/targets, fit/refit/score models, mutate counters, rewrite canonical
history, execute production, or merge PR #103/#108.

# Handoff: INC-001 RIGHTS_HMETD discovery-path correction V1

from: MAIN / `data/ca-aware-feature-basis-remediation-v1`
to: ChatGPT review
date: 2026-08-30
scope: same persisted 12-target rights capability pilot

## Review decision requested

Review the corrected implementation and the two controlling immutable replay
roots. Do not merge PR #108/#103. The corrected live provider observation and
the retained MPPA replay are intentionally separate evidence layers.

## Exact outcome

The prior pilot queried KSEI `.../masr` with `setLocale=en-US`. The corrected
path queries `.../rights-distribution` with `setLocale=id-ID`, matching the
retained official KSEI source contract.

```text
PILOT_TARGETS                         = 12
prior V1 resolved                    = 0
corrected live resolved              = 0
controlling retained replay resolved = 1 (MPPA)
corrected replay unresolved          = 11
new proven linkages                  = 0
```

MPPA is source-bound through:

```text
KSEI-15669/JKU/0626
https://web.ksei.co.id/Announcement/Files/MPPA_RIGHT_20260629_ID.pdf
SHA256 8eda1cd7fbddf5344432c88660dc8b48319b711c848ff4ec85cd3b85b010f84e
accepted Ex date 2026-06-26
```

The live corrected KSEI requests returned HTTP 500 and are retained as provider
failures. The MPPA resolution comes only from replaying prior retained official
index/PDF bytes under a new immutable root; no provider retry occurred.

## Reconciliation

```text
V10 prior:       412 source / 22 cross / 3 same / 387 events / 157 resolved / 184 unresolved / 46 non-basis
V12 corrected:   412 source / 22 cross / 3 same / 387 events / 158 resolved / 183 unresolved / 46 non-basis
linkages:        27 prior / 27 recomputed / 0 new / 0 removed-conflicting
```

```text
pilot replay root:
D:\Documents\Project\idx-ca-rights-hmetd-pilot-20260830-v3-retained-mppa
MANIFEST 71c8ecdbf322dc07a5da44175caac265b3df60dc66bb352afda8e93c5dccb07d

reconciliation root:
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v12-rights-mppa-retained
MANIFEST 963c319080b347d9fb67208c1c6264d0bcf577c688a908fc3a6cbaff40a80be1

deterministic rerun:
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v12-rights-mppa-retained-rerun
MANIFEST 7fdd836e76657f22b017c38c8a5f38a74fa151da222162a881342c16d30a50c8
comparison: PASS, 65/65 non-manifest files identical
```

## Boundaries and scientific state

```text
baseline plan: 291 unresolved physical event identities
capability-verification requests: 24
later bulk-acquisition requests: 13
bulk acquisition executed: FALSE

DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE

Phase-E                  = NOT RUN
outcomes/targets         = NOT ACCESSED
fit/refit/score          = NOT RUN
counter mutation         = NONE
canonical rewrite        = NONE
production execution     = NONE
merge                    = NONE
```

Authority blockers remain:

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY            = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY               = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
```

## Validation

```text
focused RIGHTS_HMETD tests = 6 passed
CA/integrity suite          = PASS (13 modules)
full pytest                 = PASS
compileall                  = PASS
git diff --check            = PASS
artifact hash audit         = PASS
deterministic comparison    = PASS (65/65)
exact-head CI               = PASS, run 33295545859, 382 passed, 5 warnings
```

The branch is pushed at the reviewed implementation head and is ready for
ChatGPT review. Stop here; no further production execution or scientific work
is authorized.

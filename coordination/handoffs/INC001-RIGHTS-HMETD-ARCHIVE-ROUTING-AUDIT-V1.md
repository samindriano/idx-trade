# Handoff: INC-001 RIGHTS_HMETD archive-routing audit V1

Status: `REVIEW`

Branch: `data/ca-aware-feature-basis-remediation-v1`

Implementation: `902bb084`

Artifact: `D:\Documents\Project\idx-ca-rights-hmetd-archive-routing-audit-20260830-v1`

Artifact manifest SHA256: `383c97c081425cf8a026a028de35ef9e7a192de7045b0591d8154a0020ac972e`

## Result to review

The retained 93-row KSEI document corpus establishes
`ARCHIVE_KEYS_PUBLICATION_MONTH` (93/93 archive-month/publication-month
matches), with a maximum two-calendar-month publication lead. The bounded
window was therefore candidate month plus the two preceding months.

Only two new index requests were made, for SAME `2021-01` and `2021-02`; all
other planned keys were reused from retained/prior evidence. SAME's exact row
was discovered at `2021-02`, proving one candidate-month routing false
negative. The row was:

```text
KSEI-3077/JKU/0221
https://web.ksei.co.id/Announcement/Files/SAME_RIGHT_20210303_ID.pdf
publication label: 25 Februari 2021
index SHA256: 5786ab6834f78d0771eeae44340dae32066460a5cf32c761e2e5302d490b4d62
```

The one exact PDF fetch was attempted once but local capture failed before
bytes/hash retention. It is recorded as `PROVIDER_FAILURE`; no Ex-date or
resolution was accepted and no retry is authorized. SGER and PACK remain
`ARCHIVE_ROW_STILL_NOT_DISCOVERED`.

The same raw `2021-02` index also showed out-of-scope PGJO:
`KSEI-2833/JKU/0221`, source label `Jadwal Kegiatan Penawaran Umum Terbatas
dalam rangka Penerbitan Hak Memesan Efek Terlebih Dahulu (HMETD) TOURINDO
GUIDE INDONESIA Tbk (PGJO)`, publication label `22 Februari 2021`. It was not
fetched or used to expand scope.

```text
CANDIDATE_MONTH_ROUTING_FALSE_NEGATIVE_COUNT = 1
NEW_EXACT_DOCUMENTS = 0
NEW_RESOLVED_EXACT = 0
RIGHTS_ARCHIVE_ROUTING_CONTRACT_VERDICT = RIGHTS_ARCHIVE_ROUTING_CONTRACT_PARTIAL
RIGHTS_INDEX_SOURCE_CONTRACT_VERDICT = RIGHTS_INDEX_LIVE_CONTRACT_CONDITIONALLY_REPEATABLE
FULL_RIGHTS_ACQUISITION_RECOMMENDATION = HOLD_FOR_ALTERNATE_SOURCE_PATH
```

## Counts and linkage

```text
PRIOR_PROVEN_LINKAGES = 27
RECOMPUTED_PROVEN_LINKAGES = 27
NEW_PROVEN_LINKAGES = 0
REMOVED_OR_CONFLICTING = 0

ECONOMIC_EVENTS = 387 -> 387
RESOLVED = 159 -> 159
UNRESOLVED = 182 -> 182
NON_BASIS = 46
RIGHTS_HMETD_UNRESOLVED = 69
```

No new exact evidence existed, so no economic reconciler rerun was needed.
The prior controlling V13 deterministic comparison remains 68/68 PASS.

## Validation

```text
FOCUSED_RIGHTS_TESTS = 16 passed
CA_INTEGRITY_SUITE = 149 passed
FULL_PYTEST = 392 passed
PY_COMPILE = PASS
GIT_DIFF_CHECK = PASS
ARTIFACT_HASH_VALIDATION = PASS (12/12)
DETERMINISTIC_ROUTING_PLAN_COMPARISON = PASS
EXACT_HEAD_CI = pending final push
```

The lane remains outcome-blind. Scientific verdict remains
`DATA_ADMISSION=FAIL`, `RESEARCH_ADMISSION=FAIL`,
`MODEL_PROMOTION=NOT_EVALUATED`, `HISTORICAL_APPLICATION=BLOCKED_PHASE_E_NOT_RUN`,
`REFIT_AUTHORIZED=FALSE`, `COUNTER_ACTION=NONE`. Historical negative/as-of/
complete-interval authority remains `UNSUPPORTED`/`UNKNOWN`/`UNKNOWN`.

Await ChatGPT review. Do not merge PR #108 or PR #103 and do not start broader
RIGHTS acquisition.

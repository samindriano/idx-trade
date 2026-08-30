# INC-001 RIGHTS_HMETD archive-routing audit V1

Status: `REVIEW` / outcome-blind / no merge

Date: 2026-08-30

Lane: `data/ca-aware-feature-basis-remediation-v1`

Implementation commit: `902bb084`

PR: #108 remains OPEN/DRAFT/unmerged. PR #103 remains unmerged.

## Scope and boundaries

This audit covers exactly the three prior KSEI `Right Distribution` no-match
targets SAME, SGER, and PACK. It does not acquire the remaining 69 RIGHTS
events, retry MMIX, acquire another CA family, access outcomes or targets, run
Phase-E, fit/refit/score, mutate counters, rewrite canonical historical data,
execute production, or merge a PR.

The audit wrote a plan before any new request. It reused retained/prior bodies
where available and made only two new index GETs (`2021-01`, `2021-02`), each
once, using the accepted KSEI `rights-distribution` + `setLocale=id-ID`
contract. One exact SAME PDF fetch was attempted after the discovered row; the
local capture path failed before bytes/hash retention. No retry was made.

## Local source-contract finding

The retained KSEI corpus
`D:\Documents\Project\idx-v4-3-ca-training-domain-schedule-80-ksei-20260819-v1\event_candidate_documents.csv`
contains 93 document rows and 89 unique references. All 93/93 have
`archive Month/Year == document publication month`; publication-to-first-source
event month differences are `-1:1`, `0:53`, `1:24`, `2:15`. Therefore the
smallest evidence-backed discovery window is candidate month plus the two
immediately preceding calendar months:

```text
ARCHIVE_MONTH_SEMANTIC = ARCHIVE_KEYS_PUBLICATION_MONTH
SAME = 2021-01, 2021-02, 2021-03
SGER = 2024-03, 2024-04, 2024-05
PACK = 2025-11, 2025-12, 2026-01
```

The retained initial corpus had no PGJO RIGHTS candidate row. The new
outcome-blind raw index body for SAME's planned `2021-02` month does contain
an out-of-scope official row:

```text
KSEI-2833/JKU/0221
Jadwal Kegiatan Penawaran Umum Terbatas ... HMETD ... TOURINDO GUIDE INDONESIA Tbk (PGJO).
published label: 22 Februari 2021
document ref: https://web.ksei.co.id/Announcement/Files/PGJO_RIGHT_20210226_ID.pdf
index body: D:\Documents\Project\idx-ca-rights-hmetd-archive-routing-audit-20260830-v1\provider\index_202102.body
index SHA256: 5786ab6834f78d0771eeae44340dae32066460a5cf32c761e2e5302d490b4d62
```

PGJO was not fetched, admitted, or used to expand this audit.

## Target results

| ticker | economic event ID | prior candidate month | routing result | evidence |
|---|---|---:|---|---|
| SAME | `DERIVED-cae8b02b518fd4886cbb957641bf75cb646c00d8cec959905cefde2614de9fa9` | 2021-03 | `PROVIDER_FAILURE` after a candidate-month routing false negative was found | `2021-02` HTTP 200; exact row `KSEI-3077/JKU/0221`, title publication label 25 Feb 2021, PDF fetch failed local capture; no Ex accepted |
| SGER | `DERIVED-d4dabf435934131619c850ab1fd070aee06928d24c188ac46571722c0ad2091c` | 2024-05 | `ARCHIVE_ROW_STILL_NOT_DISCOVERED` | all planned month evidence HTTP 200 / no target row |
| PACK | `DERIVED-69e5d8da2753198c085f8ba736fcded7c6b4e98205ca3ac140d12bec69a1c1ff` | 2026-01 | `ARCHIVE_ROW_STILL_NOT_DISCOVERED` | all planned month evidence HTTP 200 / no target row |

SAME's target source evidence remains source-bound and unchanged: candidate
`2021-03-01`, cum `2021-03-01`, record `2021-03-03`, distribution `2021-03-04`,
ratio `(10000 SAME : 10169 SAME-R EXP 15032021)`, source SHA
`d0a661689a375cb37c1e4e3b6503c746856e11551d8e5cef11d68ab6b7e930d2`.
The discovered archive row links to the same issuer and expected schedule
document, but the PDF bytes were not retained; this is not a transition
attestation.

SGER remains candidate `2024-05-29`, record `2024-05-29`, distribution
`2024-06-14`, ratio `(7 SGER : 18 SGER )`, source SHA
`0cbfb1b9d30783e1271e9bc5299c6f5d7931370649e42ecad6d7054edb628682`.
PACK remains candidate/record `2026-01-13`, distribution `2026-01-14`, ratio
`(5 PACK : 102 PACK-R )`, source SHA
`3e8d6e927e9caf39e2cbf46764fb69030a12534dc0dc34b5c08445dd54fc0e69`.

## Decision and recomputation

```text
CANDIDATE_MONTH_ROUTING_FALSE_NEGATIVE_COUNT = 1
NEW_EXACT_DOCUMENTS = 0
NEW_RESOLVED_EXACT = 0
RIGHTS_ARCHIVE_ROUTING_CONTRACT_VERDICT = RIGHTS_ARCHIVE_ROUTING_CONTRACT_PARTIAL
RIGHTS_INDEX_SOURCE_CONTRACT_VERDICT = RIGHTS_INDEX_LIVE_CONTRACT_CONDITIONALLY_REPEATABLE
FULL_RIGHTS_ACQUISITION_RECOMMENDATION = HOLD_FOR_ALTERNATE_SOURCE_PATH

PRIOR_PROVEN_LINKAGES = 27
RECOMPUTED_PROVEN_LINKAGES = 27
NEW_PROVEN_LINKAGES = 0
REMOVED_OR_CONFLICTING = 0

ECONOMIC_EVENTS_BEFORE = 387
ECONOMIC_EVENTS_AFTER = 387
RESOLVED_BEFORE = 159
RESOLVED_AFTER = 159
UNRESOLVED_BEFORE = 182
UNRESOLVED_AFTER = 182
NON_BASIS = 46
RIGHTS_HMETD_UNRESOLVED = 69
```

No economic reconciliation rerun was required because no new exact
transition/document evidence was retained. The controlling V13 reconciliation
and its prior deterministic 68/68 comparison remain unchanged.

## Immutable artifact and validation

```text
ARTIFACT_ROOT = D:\Documents\Project\idx-ca-rights-hmetd-archive-routing-audit-20260830-v1
MANIFEST_SHA256 = 383c97c081425cf8a026a028de35ef9e7a192de7045b0591d8154a0020ac972e
ARTIFACT_MANIFEST_VALIDATION = PASS (12 files checked, 0 mismatches)
DETERMINISTIC_ROUTING_PLAN_COMPARISON = PASS
```

Validation before push:

```text
FOCUSED_RIGHTS_TESTS = 16 passed
CA_INTEGRITY_SUITE = 149 passed
FULL_PYTEST = 392 passed
COMPILEALL / PY_COMPILE = PASS
GIT_DIFF_CHECK = PASS
```

The first focused run encountered a known Windows pytest teardown
`WinError 5` on the stale `pytest-current` temp link; the final runs used an
isolated `basetemp` and passed. This is an environment note, not a test
assertion failure.

## Scientific state and authority blockers

```text
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
MODEL_PROMOTION = NOT_EVALUATED
HISTORICAL_APPLICATION = BLOCKED_PHASE_E_NOT_RUN
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE

IDX_HISTORICAL_NEGATIVE_AUTHORITY = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
```

Next action is review only. Do not merge PR #108/#103 or start broader RIGHTS
acquisition from this checkpoint.

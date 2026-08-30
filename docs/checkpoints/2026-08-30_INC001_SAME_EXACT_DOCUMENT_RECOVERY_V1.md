# INC-001 SAME exact-document recovery V1

Status: `REVIEW` / outcome-blind / no merge

Date: 2026-08-30

Lane: `data/ca-aware-feature-basis-remediation-v1`

Implementation head: `0985162074ea1c922d378e28bedfbc15768e02c6`

PR #108 remains OPEN/DRAFT/unmerged. PR #103 remains unmerged.

## Scope and routing decision

This is a single-event recovery for SAME only. The previously accepted
source-specific routing decision remains unchanged: no event-month `+1` lookup
was added. The only retained global `lead=-1` row is ANTM
`VOLUNTARY_CONVERSION`; retained `RIGHT_DISTRIBUTION` rows have lead `0:7` and
`+1:3`, with no `-1` row.

No SGER/PACK lookup, index rediscovery, alternate URL, other RIGHTS acquisition,
MMIX retry, other CA-family acquisition, Phase-E, outcomes/targets, model work,
counter mutation, canonical rewrite, production execution, or merge occurred.

## Exact recovery

The exact retained official row was `KSEI-3077/JKU/0221`, archive month
`2021-02`, publication label `25 February 2021`, with href
`https://web.ksei.co.id/Announcement/Files/SAME_RIGHT_20210303_ID.pdf`.

Exactly one PDF GET was made. It returned HTTP 200 and a valid 92,805-byte PDF:

```text
SAME_PDF_REQUEST_RESULT = HTTP_200_VALID_PDF
SAME_DOCUMENT_REFERENCE = KSEI-3077/JKU/0221
SAME_DOCUMENT_SHA256 = 1281dc227ca94d417f074cff17396ffbdfab4b464669ff2251f77c3b247dc0c0
SAME_EXPLICIT_EX_SEMANTIC = TRUE
SAME_ACCEPTED_EX_DATE = 2021-03-02
SAME_FINAL_CLASSIFICATION = RESOLVED_EXACT
```

The PDF explicitly states the regular-market and negotiation-market Ex date.
Record date `2021-03-03` and distribution date `2021-03-04` were used only to
verify event mechanics, not as transition dates.

## Linkage and reconciliation

The exact PDF resolves the existing SAME economic event. It supplies no second
source-representation pair, so no new linkage was added:

```text
PRIOR_PROVEN_LINKAGES = 27
RECOMPUTED_PROVEN_LINKAGES = 27
NEW_PROVEN_LINKAGES = 0
REMOVED_OR_CONFLICTING = 0
```

The normal fail-closed reconciler was run over the immutable V13 source and
adjudication inputs with the new source-bound transition attestation. The
canonical V13 root was not overwritten:

```text
SOURCE_EVIDENCE_ROWS = 412 -> 412
CROSS_SOURCE_COLLAPSES = 22 -> 22
SAME_SOURCE_COLLAPSES = 3 -> 3
ECONOMIC_EVENTS = 387 -> 387
RESOLVED = 159 -> 160
UNRESOLVED = 182 -> 181
NON_BASIS = 46 -> 46
RIGHTS_HMETD_UNRESOLVED = 69 -> 68
```

## Immutable outputs

```text
RECOVERY_ROOT = D:\Documents\Project\idx-ca-same-exact-document-recovery-20260830-v2
RECOVERY_MANIFEST_SHA256 = a08f27a6cf20730b824c87b138e84e6e17f851769b565d2c357ff8d1e7bd3353

SUCCESSOR_RECONCILIATION_ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v14-same-exact
SUCCESSOR_RECONCILIATION_MANIFEST_SHA256 = c095c00c31691c07cbf4d50c447abafde9b00db0e93f8184ea6e9a83b4a1990b
DETERMINISTIC_RERUN_ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v14-same-exact-rerun
DETERMINISTIC_RERUN_MANIFEST_SHA256 = aa482653a0e0c037e18397a3108b2dd331c9aeb4b7f9ff8e7d8d625060a3d548
DETERMINISTIC_COMPARISON = PASS (13/13 non-manifest files identical)
```

The prior archive-routing V1 root remains immutable and is not replaced.

## Source-path decision and authority blockers

```text
RIGHTS_ARCHIVE_ROUTING_CONTRACT_VERDICT = RIGHTS_ARCHIVE_ROUTING_CONTRACT_PARTIAL
RIGHTS_INDEX_SOURCE_CONTRACT_VERDICT = RIGHTS_INDEX_LIVE_CONTRACT_CONDITIONALLY_REPEATABLE
FULL_RIGHTS_ACQUISITION_RECOMMENDATION = HOLD_FOR_ALTERNATE_SOURCE_PATH

IDX_HISTORICAL_NEGATIVE_AUTHORITY = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
```

One exact positive event does not certify the remaining 68 RIGHTS events or
population-wide historical completeness.

## Validation and scientific state

Validation was run before this documentation update:

```text
FOCUSED_RIGHTS_AND_RECONCILIATION_TESTS = 23 passed
CA_INTEGRITY_SUITE = 131 passed (13 modules)
FULL_PYTEST = 392 passed
COMPILEALL = PASS
GIT_DIFF_CHECK = PASS
ARTIFACT_HASH_VALIDATION = PASS (3 roots, zero mismatches)
DETERMINISTIC_RECONCILIATION = PASS (13/13 non-manifest files identical)
```

The exact-head CI warning about GitHub Actions Node.js 20 is a warning
annotation, not a test failure. Exact-head CI will be recorded after this
checkpoint commit.

```text
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
MODEL_PROMOTION = NOT_EVALUATED
HISTORICAL_APPLICATION = BLOCKED_PHASE_E_NOT_RUN
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

This checkpoint is returned for ChatGPT review. Stop; do not broaden the scope
or merge PR #103/#108.

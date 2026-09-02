# INC-001 RIGHTS_HMETD discovery-path correction V1

date: 2026-08-30
lane: `data/ca-aware-feature-basis-remediation-v1`
scope: same persisted 12-target capability pilot only

## Decision summary

The prior bounded pilot's KSEI route was wrong. It queried the general MASR
category (`.../masr`), while HMETD documents are published under the official
`.../rights-distribution` category. The corrected implementation uses the
rights-specific endpoint and the retained source contract
`KSEI_RIGHTS_DISTRIBUTION_OFFICIAL_INDEX_CONTRACT`.

This correction does not expand the sample, rewrite V10/canonical history, or
claim historical completeness. The live corrected request is retained as a
separate provider observation because KSEI returned HTTP 500 for the six KSEI
month requests. A separate immutable offline replay retains the known-positive
MPPA index/PDF bytes so the prior false negative is not treated as absence.

## Immutable evidence pins

```text
controlling V9 manifest:
dcc5e05ca3bc5fe7da148629a26fb913a6e85b92a88cbc88180cfde05eec30cc

prior pilot root:
D:\Documents\Project\idx-ca-rights-hmetd-pilot-20260830-v1
prior pilot MANIFEST:
4f40cbc99457978f72a4333edbf734b59d09bb7a71586e6922f37c3a085bf24a

corrected live root:
D:\Documents\Project\idx-ca-rights-hmetd-pilot-20260830-v2-rights-index
corrected live MANIFEST:
6011c88fb009f80070566ff6cf5c9c2c5a8e43afbc8156d5d8cf2d25a396f3e7

controlling corrected replay root:
D:\Documents\Project\idx-ca-rights-hmetd-pilot-20260830-v3-retained-mppa
controlling replay MANIFEST:
71c8ecdbf322dc07a5da44175caac265b3df60dc66bb352afda8e93c5dccb07d

retained official source root:
D:\Documents\Project\idx-v4-3-ca-training-domain-schedule-80-ksei-20260819-v1
retained source MANIFEST:
a7b10ded6246102d6d7858546fdb955ad426bf9a18f762239245a7253f801765
```

The prior pilot selection files are byte-identical in the corrected live root.
No new selection was performed.

## Exact root cause and source contract

The prior runner used:

```text
https://web.ksei.co.id/publications/corporate-action-schedules/masr
.../masr?Month=06&Year=2026&setLocale=en-US
```

The source-native HMETD route is:

```text
https://web.ksei.co.id/publications/corporate-action-schedules/rights-distribution
.../rights-distribution?Month=06&Year=2026&setLocale=id-ID
```

The retained MPPA index row proves the parser assumptions for this known
positive: `<tr>/<td>` structure, first-cell PDF href, Indonesian HMETD title,
`(MPPA)` ticker token, and `.pdf` href all parse correctly. The previous
`MASR` contract label was also incorrect provenance. Month/year is only a
bounded discovery routing key; it is not a transition semantic and no candidate
date is promoted to an Ex date.

The corrected parser accepts the source-specific rights contract while retaining
explicit regular-market Ex parsing. No date proximity or document-count rule
creates a linkage.

## MPPA retained official evidence

```text
index source ref:
https://web.ksei.co.id/publications/corporate-action-schedules/rights-distribution?Month=06&Year=2026&setLocale=id-ID
index raw SHA256:
1f6d4de6ceee0a0a97ca0d1eef9f9a42826d3480c1b8dfe0e118a4dca912c99f

document reference: KSEI-15669/JKU/0626
document source ref:
https://web.ksei.co.id/Announcement/Files/MPPA_RIGHT_20260629_ID.pdf
document SHA256:
8eda1cd7fbddf5344432c88660dc8b48319b711c848ff4ec85cd3b85b010f84e
document bytes: 40234
publication date: 2026-06-19
```

The retained PDF explicitly states:

```text
Cum Regular/Negotiation: 2026-06-25
Ex Regular/Negotiation: 2026-06-26
Recording: 2026-06-29
Distribution: 2026-06-30
```

Only `2026-06-26` is accepted as `REGULAR_MARKET_EX_DATE`. The MPPA event's
prior candidate/record date is not used as the transition date.

## Same-12 results

The persisted pilot has exactly 12 targets: six IDX and six KSEI, with 12
unique tickers. Results are kept in three distinct states:

| Result layer | Resolved | Official event evidence / document unavailable | Provider failure | No document | Semantic insufficient | Ambiguous |
|---|---:|---:|---:|---:|---:|---:|
| Prior V1 (`MASR`) | 0 | 6 | 0 | 6 | 0 | 0 |
| Corrected live (`rights-distribution`) | 0 | 6 | 6 | 0 | 0 | 0 |
| Corrected retained replay (controlling) | 1 | 6 | 5 | 0 | 0 | 0 |

For MPPA specifically:

```text
prior V1:                    NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED
corrected live:              PROVIDER_DISCOVERY_FAILURE (HTTP 500)
controlling retained replay: RESOLVED_EXACT
accepted transition:         2026-06-26
```

The replay is not a new provider call or retry. It copies and hashes the
retained official index/PDF bytes into the new immutable root and independently
parses them. The six IDX rows remain event evidence without an exposed exact
transition document. The remaining five KSEI rows remain provider-blocked.

```text
PILOT_TARGETS                         = 12
PILOT_RESOLVED_CONTROLLING            = 1
RIGHTS_UNRESOLVED_AFTER_REPLAY        = 70
RIGHTS_WITH_PROVEN_PATH               = 1
RIGHTS_WITHOUT_PROVEN_PATH            = 11
NEW_PROVEN_LINKAGES                   = 0
```

No historical completeness or negative authority is claimed.

## Reconciliation impact

The controlling local replay was consumed by the existing fail-closed
reconciler. Only the MPPA source representation receives a source-bound
transition attestation. No new source-pair evidence exists, so the 27 proven
linkages are preserved exactly.

```text
                         V10 prior   corrected replay   delta
source evidence rows          412            412            0
cross-source collapses         22             22            0
same-source collapses           3              3            0
economic events               387            387            0
resolved transitions          157            158           +1
unresolved transitions        184            183           -1
non-basis exclusions            46             46            0
```

```text
prior proven linkages       = 27
recomputed proven linkages  = 27
new proven linkages         = 0
removed/conflicting         = 0
```

Controlling reconciliation roots:

```text
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v12-rights-mppa-retained
MANIFEST: 963c319080b347d9fb67208c1c6264d0bcf577c688a908fc3a6cbaff40a80be1

D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v12-rights-mppa-retained-rerun
MANIFEST: 7fdd836e76657f22b017c38c8a5f38a74fa151da222162a881342c16d30a50c8
```

Deterministic non-manifest comparison: **65/65 files identical**.

The V1/V2/V3 pilot roots and V10 remain immutable intermediates. The V3
retained replay and V12 reconciliation are the controlling corrected results;
the V2 live provider observation must not be presented as the MPPA result by
itself.

## Future plan and authority blockers

The baseline acquisition plan remains exactly 291 unresolved physical event
identities, with 24 capability-verification requests and 13 later bulk
acquisition requests. This same-12 pilot did not consume or expand either plan.

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY          = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY             = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
```

The scientific verdict is unchanged:

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

## Validation

```text
focused RIGHTS_HMETD tests = 6 passed
CA/integrity suite          = PASS (13 modules)
full pytest                 = PASS (exit 0, 100% completion)
compileall                  = PASS
git diff --check            = PASS
manifest/hash audit         = PASS (all listed outputs, zero mismatches)
deterministic replay        = PASS (65/65 non-manifest files identical)
exact-head GitHub Actions   = PASS, run 33295545859, 382 passed, 5 warnings
```

No Phase-E, provider work beyond the same-12 corrected lookup, outcomes or
targets, fit/refit/score, counter mutation, canonical historical rewrite,
production execution, or merge was performed.

This checkpoint is ready for ChatGPT review. Do not merge PR #108/#103 and do
not start any further production or scientific execution from this handoff.

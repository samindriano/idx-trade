# Handoff: INC-001 transition-capability probe V1

from: MAIN / Codex
to: ChatGPT review
task_id: `INC001-TRANSITION-CAPABILITY-PROBE-V1`
lane: `data/ca-aware-feature-basis-remediation-v1`

## Decision

`NO-GO for bulk acquisition or scientific execution`: a bounded 8-event
official-source capability probe completed. It proves exact transition
semantics for 3 representative events only; it does not certify the remaining
291 unresolved transitions, historical no-event coverage, or KSEI completeness.

## Control pins

```text
implementation/input HEAD = f6f4ec027665fe8c33632cc211923a7d6503a7e2
remote equality            = VERIFIED
artifact root              = D:\Documents\Project\idx-ca-transition-capability-probe-20260829-v1
artifact MANIFEST SHA-256  = 4949b9e501d0c751f9c7a51093daa88a0cbcb0da87d132836ffe0dd9894bc8dd
```

The artifact contains the exact selection rule, retained request/document
bytes and hashes, PDF text/render checks, index-to-document linkage, all 8
row-level verdicts, capability summary, and a 291-row future acquisition plan.

## Result

```text
RIGHTS_HMETD       = PARTIAL_HISTORICAL_CAPABILITY; 2 tested, 1 resolved
STOCK_SPLIT        = HISTORICAL_SOURCE_PATH_PROVEN; 2 tested, 2 resolved
MANDATORY_CONVERSION = CAPABILITY_NOT_PROVEN; 2 tested, 0 resolved
VOLUNTARY_CONVERSION = CAPABILITY_NOT_PROVEN; 2 tested, 0 resolved

REPRESENTATIVE_EVENTS_NEWLY_RESOLVED = 3
PHYSICAL_EVENT_CENSUS                = 412
BASELINE_RESOLVED_TRANSITIONS        = 121
BASELINE_UNRESOLVED_TRANSITIONS      = 291
BASELINE_CENSUS_MUTATED              = FALSE
```

Resolved events and controlling semantics:

1. PGJO `RIGHTS_HMETD`: official KSEI `KSEI-2833/JKU/0221`, exact regular-
   market ex date 2021-02-25.
2. ERAA `STOCK_SPLIT`: official KSEI `KSEI-4844/JKU/0321`, first new-basis
   regular-market trading date 2021-03-31.
3. MLPT `STOCK_SPLIT`: official KSEI `KSEI-18691/JKU/0726`, first new-basis
   regular-market trading date 2026-07-21.

The complete event identities, references, hashes, and unresolved reasons are
in `representative_linkage_results.csv`. The 3 probe resolutions are staged
evidence only; the baseline census is not rewritten.

## Acquisition plan and authority gaps

The full future event-level plan remains exactly 291 identities:

```text
RIGHTS_HMETD           72
STOCK_SPLIT            41
MANDATORY_CONVERSION   39
VOLUNTARY_CONVERSION   93
CAPITAL_RESTRUCTURING  19
BONUS_SHARES           11
STOCK_DIVIDEND          7
MERGER                  5
UNKNOWN_TAXONOMY        4
TOTAL                 291
```

The 8-row capability-verification probe is complete. Additional capability
verification requests in this handoff: `0`. Later bulk acquisition of the 291
identities requires explicit future authorization and must remain separate from
this probe.

The current IDX snapshot still does not support historical negative/no-event
authority; `IDX_HISTORICAL_ASOF_AUTHORITY=UNKNOWN`. Parsed KSEI pages do not
prove a complete historical interval. Conversion events remain unresolved
unless an official source explicitly establishes the new economic/share basis
trading boundary. No candidate date, recording date, distribution date,
listing date, exercise/maturity date, or tender/payment date was substituted.

## Scientific and authorization state

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE

FULL_291_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED              = FALSE
REFIT_AUTHORIZED                = FALSE
COUNTER_ACTION                  = NONE
```

## Validation and stop

Artifact hashes/counts, `git diff --check`, and `py_compile` passed. The
pushed implementation head's exact-head CI succeeded in run `33241262804`
(job `99070891938`): 334 passed with one non-blocking Node.js 20 action
deprecation warning. No further IDX acquisition was performed after the
accepted paginated capture; no Phase-E, outcomes, models, counters, canonical
history, taxonomy, or PR merge was touched.

This handoff is complete and returned for ChatGPT review. Stop.

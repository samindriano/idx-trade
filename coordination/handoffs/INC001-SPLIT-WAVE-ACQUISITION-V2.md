# Handoff: INC-001 split/reverse transition acquisition wave V2

from: local Codex continuation
to: ChatGPT review
task: `INC001-SPLIT-WAVE-ACQUISITION-V2`
lane: `data/ca-aware-feature-basis-remediation-v1`

## Review decision requested

Please review the immutable acquisition and reconciliation successors below.
Do not merge PR #108/#103 and do not run Phase-E, providers, outcomes,
model/refit/scoring, counter actions, or canonical historical rewrites.

## Exact result

The authorized V4 residual scope was exactly 21 `STOCK_SPLIT` events plus one
BBRM `REVERSE_SPLIT` event. The stale capability unit
`CAPABILITY-V11-KSEI-REPRESENTATIVE-3` is closed as
`CLOSED_PREVIOUSLY_EXECUTED_NO_RETRY`; no AADI/ADRO/AALI retry occurred.

Acquisition:

```text
ROOT     = D:\Documents\Project\idx-ca-stock-split-acquisition-20260829-v3
MANIFEST = cdd96f746df3edf224f314a82993aac61d79324b4e8b46d96bcad74fe673a1a6
```

The underlying official-source wave made five exact HTTP 200 fetches once;
the corrected V3 root reused those bytes without redownload. Results:

```text
RESOLVED_EXACT                         = 2  (HEAL, SCMA)
DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT   = 1  (BBRM)
DOCUMENT_NOT_FOUND                     = 19 (retained official index scope)
```

Only explicit `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE` was accepted.
BBRM's official reverse-stock plan/odd-lot documents do not prove that
semantic for the 2022-02-17 event; it remains unresolved. Not-found is not a
historical negative-authority claim.

Reconciliation successor:

```text
ROOT         = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v7-split-wave
MANIFEST     = 575982a3f1f179ff3b0267d40589f4886db6f593be49bcedb8aa1885f1b2725d
RERUN_ROOT   = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v7-split-wave-rerun
RERUN_SHA256 = fc7aee5784b0a78dfc34015c8ffd910bce7debcda149d1ab82aa3af0adbe9f21
```

Counts:

```text
412 source rows; 389 physical events; 155 resolved transitions;
188 unresolved transitions; 46 non-basis exclusions.
Before V3: 412 / 389 / 153 / 190 / 46.
```

Physical-event count did not change. The future plan partitions all 188
unresolved IDs into residual split/reverse (20), rights (71), source-
authority (46), operational taxonomy (47), and unknown taxonomy (4); the
capability verification unit is closed and has zero event IDs.

## Invariants and blockers

The three authority blockers remain:

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY           = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY               = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
```

Scientific state remains:

```text
DATA_ADMISSION=FAIL
RESEARCH_ADMISSION=FAIL
MODEL_PROMOTION=NOT_EVALUATED
HISTORICAL_APPLICATION=BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED=FALSE
COUNTER_ACTION=NONE
PR_108_MERGED=FALSE
PR_103_MERGED=FALSE
```

## Validation

Local focused tests: 48 passed. CA/integrity suite: 131 passed. Full pytest:
370 passed. `py_compile`: 84 files passed. `git diff --check`: PASS.
V7/V8 deterministic comparison: 14/14 non-manifest files identical, PASS.
Exact-head GitHub Actions run is recorded after push in the final update to
this handoff/checkpoint.

Recommended next action: independent ChatGPT review of the immutable V7
reconciliation and future plan. No merge or production execution.

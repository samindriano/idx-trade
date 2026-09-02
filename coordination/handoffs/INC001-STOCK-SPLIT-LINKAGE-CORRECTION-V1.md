# Handoff: INC-001 stock-split linkage correction V1

from: MAIN / Codex  
to: ChatGPT review  
task_id: `INC001-STOCK-SPLIT-LINKAGE-CORRECTION-V1`  
lane: `data/ca-aware-feature-basis-remediation-v1`  
implementation input HEAD: `014558407c249af92730d648e69663c7eef1c8bf`

## Decision

`NO-GO for acquisition or scientific execution`: the retained-byte linkage
correction is complete. It admits exactly two new source-bound same-economic-
event linkages and leaves all scientific and provider boundaries unchanged.

## Required review values

```text
AKRA_PAIR_CLASSIFICATION = PROVEN_SAME_ECONOMIC_EVENT
HRUM_PAIR_CLASSIFICATION = PROVEN_SAME_ECONOMIC_EVENT

PRIOR_PROVEN_LINKAGES       = 25
RECOMPUTED_PROVEN_LINKAGES  = 27
NEW_PROVEN_LINKAGES         = 2
REMOVED_OR_CONFLICTING      = 0
V8_LINKAGE_FREEZE_BUG       = CONFIRMED

SOURCE_EVIDENCE_ROWS        = 412
CROSS_SOURCE_COLLAPSES_BEFORE = 20
CROSS_SOURCE_COLLAPSES_AFTER  = 22
SAME_SOURCE_COLLAPSES         = 3
ECONOMIC_EVENTS_BEFORE        = 389
ECONOMIC_EVENTS_AFTER         = 387
RESOLVED_BEFORE               = 159
RESOLVED_AFTER                = 157
UNRESOLVED_BEFORE             = 184
UNRESOLVED_AFTER              = 184
NON_BASIS                     = 46
```

The full linkage IDs, refs, hashes, six-row audit, representation mapping,
and residual geometry are in the [checkpoint](../../docs/checkpoints/2026-08-29_INC001_STOCK_SPLIT_LINKAGE_CORRECTION_V1.md)
and in the controlling artifact's `linkage_delta_report.csv` and
`source_to_economic_mapping.csv`.

## Controlling artifact

```text
RECONCILIATION_ARTIFACT_ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v9-stock-split-linkage-correction-final
MANIFEST_SHA256              = dcc5e05ca3bc5fe7da148629a26fb913a6e85b92a88cbc88180cfde05eec30cc
DETERMINISTIC_COMPARISON     = PASS; 20/20 non-manifest files identical against final-rerun2
RERUN_ROOT                   = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v9-stock-split-linkage-correction-final-rerun2
RERUN_MANIFEST_SHA256        = aef0b88b212871bf77b52211baa427b5a20fe9a808fb880d79e26ddb6e859835
```

The baseline acquisition plan remains exactly 291 unresolved physical events:
24 capability-verification requests and 13 later bulk requests. The current
source capability verdict remains:

```text
STOCK_SPLIT_SOURCE_CAPABILITY = CAPABILITY_NOT_RELIABLY_REPEATABLE
```

## Scientific state and boundaries

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY            = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY               = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
DATA_ADMISSION                              = FAIL
RESEARCH_ADMISSION                          = FAIL
MODEL_PROMOTION                             = NOT_EVALUATED
HISTORICAL_APPLICATION                      = BLOCKED_PHASE_E_NOT_RUN
PHASE_E_AUTHORIZED                          = FALSE
REFIT_AUTHORIZED                            = FALSE
COUNTER_ACTION                              = NONE
```

No provider/network data call, provider retry, BBRM retry, RIGHTS_HMETD or
other CA acquisition, Phase-E, outcomes/targets access, model fit/refit/
scoring, counter mutation, canonical historical rewrite, production execution,
or merge of PR #108/#103 occurred. The retained V5 discovery artifact,
predecessor V8 final2, and all prior evidence remain immutable.

## Validation

```text
FOCUSED_TESTS       = 13 passed
CA_INTEGRITY_TESTS  = 158 passed
FULL_PYTEST         = 376 passed
COMPILEALL          = PASS
DIFF_CHECK          = PASS
ARTIFACT_HASHES     = PASS; 0 retained-document hash failures
DETERMINISTIC_RERUN = PASS; 20/20 non-manifest files byte-identical
EXACT_HEAD_CI       = PASS; run 33263200103 on `cb52d809`; 376 passed, 5 non-blocking Node.js 20 warnings
```

Return for ChatGPT review after exact-head CI. Do not merge and do not run
further production or scientific execution.

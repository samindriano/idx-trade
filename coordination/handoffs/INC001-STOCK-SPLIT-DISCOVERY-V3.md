# Handoff: INC-001 bounded STOCK_SPLIT discovery V3

from: local Codex continuation
to: ChatGPT review
task: `INC001-STOCK-SPLIT-DISCOVERY-V3`
lane: `data/ca-aware-feature-basis-remediation-v1`

## Decision requested

Review the controlling V5 discovery and V8 final2 reconciliation roots. Do
not merge PR #108/#103 and do not run Phase-E, providers, outcomes, model
work, refit/scoring, counter actions, or canonical historical rewrites.

## Exact bounded result

The only discovery scope was the 19 residual V7 `STOCK_SPLIT` economic events.
The live official-source root is:

```text
ROOT     = D:\Documents\Project\idx-ca-stock-split-discovery-20260829-v2
MANIFEST = 88a4483a07c970d65bbceb8595031b4a25f8d6a692d736202da08b8026a96ca3
```

The controlling normalized/reuse root is:

```text
ROOT     = D:\Documents\Project\idx-ca-stock-split-discovery-20260829-v5
MANIFEST = df44d4f17fe3062ba3c2b97ad773b180fcd0a52d8f74000c0f91f768f0eacfcc
```

Classifications are:

```text
RESOLVED_EXACT                         = 6
NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED = 2  (DIVA two rows)
PROVIDER_DISCOVERY_FAILURE             = 11
```

The exact rows are AKRA (two), AMOR (one), HRUM (two), and MTDL (one). Only
explicit `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE` semantics were
accepted. The provider-failure rows are not negative historical claims.
The path verdict is `CAPABILITY_NOT_RELIABLY_REPEATABLE` and the historical
negative/as-of/complete-interval authority blockers remain unsupported or
unknown.

## Controlling reconciliation

```text
ROOT     = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v8-stock-split-discovery-final2
MANIFEST = df5e622da2e7577090735e7c2e4905502bb4432f2d29c175c10c966ea66020c1
```

Deterministic rerun:

```text
ROOT     = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v8-stock-split-discovery-final2-rerun
MANIFEST = 662e402b7b4d07ef33af7d0d7bcd8ce07a05ea107a71ab023d3d461819e99be6
COMPARE  = 15/15 non-manifest files identical
```

Before/after V7 to V8 final2:

```text
412 source rows; 389 physical events; 159 resolved transitions;
184 unresolved transitions; 46 non-basis exclusions;
20 cross-source collapses; 3 same-source collapses.
```

The physical-event/linkage census is intentionally unchanged from V7. The
wave adds four transition attestations, not source linkages or physical
events. BBRM remains unresolved and unchanged.

The final acquisition plan is `future_acquisition_plan_v11_291.json` and
conserves the exact baseline 291 unresolved physical-event identities:

```text
capability-verification requests = 24
later bulk-acquisition requests = 13
baseline unresolved events      = 291
```

The separate post-wave residual count of 184 is accounting only. The current
19-row wave is not a bulk acquisition and does not rewrite the 291 baseline.

## Scientific and safety state

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

No Phase-E, outcome/target access, model/refit/scoring, counter mutation,
canonical historical rewrite, production execution, or merge occurred.

## Validation completed

```text
focused tests     = 33 passed
CA/integrity      = 152 passed across 14 files
full pytest       = 372 passed
py_compile        = PASS (86 Python files)
git diff --check  = PASS
determinism       = 15/15 non-manifest files identical
```

Exact-head GitHub Actions run `33260926312` on `af20528c` passed with
`372 passed, 5 warnings`. The GitHub annotation is the Node.js 20 deprecation
for `actions/checkout@v4` and `actions/setup-python@v5`; report it as a warning
and not as zero-warning success. This handoff stops at ChatGPT review; no
merge or production execution should follow without a separate decision.

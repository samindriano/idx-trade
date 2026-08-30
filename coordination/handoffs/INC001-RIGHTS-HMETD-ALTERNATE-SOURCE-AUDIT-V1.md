# Handoff: INC-001 alternate official RIGHTS_HMETD source-path audit V1

from: MAIN / `data/ca-aware-feature-basis-remediation-v1`
to: ChatGPT review
date: 2026-08-30
scope: bounded eight-event alternate official-source capability verification

## Review pins

```text
current remote HEAD: 5fc67a6f5dc33fd46c353c25b925d587e97f0d0d
controlling V14 root: D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v14-same-exact
controlling V14 manifest: c095c00c31691c07cbf4d50c447abafde9b00db0e93f8184ea6e9a83b4a1990b
selection root: D:\Documents\Project\idx-ca-rights-hmetd-alternate-source-audit-20260830-v1-selection
selection manifest: 5e52127d2c007e40a06d2397f6f6fc08562b68b7296f2d5b95dddc2828e5e344
controlling audit root: D:\Documents\Project\idx-ca-rights-hmetd-alternate-source-audit-20260830-v4
controlling audit manifest: 3b5b1035804275871831c176f82e5e2a8dfc777dfc4ea2fbb76dec0576b999f8
execution intermediate root: D:\Documents\Project\idx-ca-rights-hmetd-alternate-source-audit-20260830-v2
execution intermediate manifest: 2384a4c8989401d19bdfbbff144e0e8afdb60698f064187db7bb8413b9338e8f
assessment intermediate root: D:\Documents\Project\idx-ca-rights-hmetd-alternate-source-audit-20260830-v3
assessment intermediate manifest: 0c52c63f28efe7ae2c2ed32f53c980920503d1aab75e89ec70855909aba7ab94
```

## Result

Exactly eight V14 unresolved RIGHTS economic events were frozen before
provider access. SGER 2024 and PACK 2026 were mandatory members; MPPA, GMFI,
and SAME were excluded as already resolved. The selection was 3 IDX-origin and
5 KSEI-origin events across early/middle/recent dates.

The official IDX announcement endpoint was called once per event. All eight
requests returned HTTP 403. Raw response bytes and hashes are retained in the
controlling audit root. No attachment was fetched, no issuer path was guessed,
and no KSEI retry was performed.

```text
RESOLVED_EXACT = 0
SEMANTIC_INSUFFICIENT = 0
LINKAGE_AMBIGUOUS = 0
DOCUMENT_UNAVAILABLE = 0
NO_ALTERNATE_OFFICIAL_DOCUMENT = 0
PROVIDER_FAILURE = 8

IDX_RIGHTS_DOCUMENT_PATH = ALTERNATE_OFFICIAL_PATH_NOT_RELIABLY_REPEATABLE
ISSUER_RIGHTS_DOCUMENT_PATH = NOT_TESTED_IN_BOUNDED_PILOT
ALTERNATE_RIGHTS_SOURCE_CAPABILITY = ALTERNATE_OFFICIAL_PATH_PARTIAL
```

The aggregate is deliberately partial: the IDX path failed uniformly, but the
issuer-official path was not tested. This is not a historical negative or
completeness claim. V4 adds no new provider call. It verifies all 14
hash-bound V14 outputs and all 18 hash-bound execution outputs. Its only
successful-page rule is explicit single-page completeness (`ResultCount` equals
`Replies` within page size); otherwise the event remains a provider failure.
Document resolution additionally requires official source URL/SHA, ticker,
rights semantics, all target dates, ratio mechanics, and a unique
attachment-to-event association. Ticker/date proximity and naked status labels
are insufficient.

Linkage recomputation found no accepted delta:

```text
PRIOR_PROVEN_LINKAGES = 27
RECOMPUTED_PROVEN_LINKAGES = 27
NEW_PROVEN_LINKAGES = 0
REMOVED_OR_CONFLICTING = 0
```

No successor reconciliation was created because no exact transition or new
linkage evidence changed V14. The controlling scientific state remains:

```text
SOURCE_EVIDENCE_ROWS = 412
ECONOMIC_EVENTS = 387
RESOLVED = 160
UNRESOLVED = 181
NON_BASIS = 46
RIGHTS_HMETD_UNRESOLVED = 68
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

## Validation and boundaries

```text
focused alternate/economic tests = PASS (28/28)
CA/integrity suite = PASS (131/131)
full pytest = PASS (403/403)
compileall = PASS
git diff --check = PASS
artifact hash validation = PASS
deterministic assessment replay = PASS (V4 from V2, no provider calls)
exact-head CI = PASS, run 33309789585, head 5fc67a6f5dc33fd46c353c25b925d587e97f0d0d, pytest job 2m32s
```

The exact-head run emitted one GitHub deprecation annotation covering
`actions/checkout@v4` and `actions/setup-python@v5` (Node.js 20 on Node.js 24),
reported separately from the successful test result.

PR #108 remains OPEN/DRAFT/unmerged. PR #103 remains OPEN/DRAFT/unmerged.
No full residual RIGHTS acquisition, KSEI retry, other CA acquisition,
Phase-E, outcomes, model work, counter action, canonical rewrite, production
execution, or merge was performed.

Required review decision: preserve the controlling V4 alternate audit as
`ALTERNATE_OFFICIAL_PATH_PARTIAL`; separately authorize any future issuer-official
path probe before considering wider RIGHTS acquisition. V2/V3 remain immutable
intermediates and are not controlling. Stop here.

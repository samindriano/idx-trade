# INC-001 alternate official RIGHTS_HMETD source-path audit — V1

Date: 2026-08-30
Lane: `data/ca-aware-feature-basis-remediation-v1`
Scope: bounded eight-event alternate official-source capability audit only

This checkpoint is outcome-blind. It does not authorize full residual RIGHTS
acquisition, KSEI retry/widening, other CA-family acquisition, Phase-E,
outcome/target access, model fit/refit/scoring, counter mutation, canonical
historical rewrite, production execution, or merge of PR #103/#108.

Final lane HEAD before this documentation pin: `117274b8cfac6bf23577cfe30d9bdd11936f6077`.

## Controlling input and immutable artifacts

The controlling economic reconciliation was V14:

```text
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v14-same-exact
MANIFEST SHA-256: c095c00c31691c07cbf4d50c447abafde9b00db0e93f8184ea6e9a83b4a1990b
```

The selection was frozen before provider access:

```text
D:\Documents\Project\idx-ca-rights-hmetd-alternate-source-audit-20260830-v1-selection
MANIFEST SHA-256: 5e52127d2c007e40a06d2397f6f6fc08562b68b7296f2d5b95dddc2828e5e344
```

The controlling alternate-source audit is the new immutable offline assessment
successor of the one-pass execution root. V4 supersedes V3 as controlling:

```text
D:\Documents\Project\idx-ca-rights-hmetd-alternate-source-audit-20260830-v4
MANIFEST SHA-256: 3b5b1035804275871831c176f82e5e2a8dfc777dfc4ea2fbb76dec0576b999f8
```

V2 and V3 remain immutable intermediates. V2 is the one-pass execution root;
V3 changed only the aggregate verdict. V4 preserves the same captured provider
bytes and adds the evidence-validation policy/results without any provider
call:

```text
D:\Documents\Project\idx-ca-rights-hmetd-alternate-source-audit-20260830-v2
MANIFEST SHA-256: 2384a4c8989401d19bdfbbff144e0e8afdb60698f064187db7bb8413b9338e8f
D:\Documents\Project\idx-ca-rights-hmetd-alternate-source-audit-20260830-v3
MANIFEST SHA-256: 0c52c63f28efe7ae2c2ed32f53c980920503d1aab75e89ec70855909aba7ab94
```

No successor economic reconciliation was created because no exact transition
evidence or accepted linkage changed V14.

## Frozen pilot selection

V14 contained exactly 68 unresolved `RIGHTS_HMETD` economic events. The pilot
contains eight unique events, including the required SGER 2024 and PACK 2026
events, with three IDX-origin and five KSEI-origin representations. MPPA,
GMFI, and SAME were excluded because their exact transitions are already
resolved.

```text
DERIVED-6d10cae7c3e5f821c99355eab140011a112fe1a7aed5313eb0dc3886df6e3920 | ARTO | KSEI | EARLY
DERIVED-837102e38acbdfe060416896abe4d93ff7aefc853a3f671f82d4c9e3edd3f4a5 | SMCB | IDX  | EARLY
DERIVED-58a63423fb37d46f46ae220bb4501a67bfbdbe5a7f1e226cfc95dc1cbc681f1b | PANR | IDX  | MIDDLE
DERIVED-d4dabf435934131619c850ab1fd070aee06928d24c188ac46571722c0ad2091c | SGER | KSEI | MIDDLE
DERIVED-19e495e7274bc56ed99567db045856481765749c9f59c550064444adce6d4f7c | IMJS | KSEI | MIDDLE
DERIVED-69e5d8da2753198c085f8ba736fcded7c6b4e98205ca3ac140d12bec69a1c1ff | PACK | KSEI | MIDDLE
DERIVED-8b72adb36efaf999ebc0904c1392ba13bfc4aa21b794a580756de04e13a7d664 | BABY | KSEI | RECENT
DERIVED-82eec91418f1b90d1704cbbd2c7680764c67d4ef130d7517486c7c01aeef35ad | BNBR | IDX  | RECENT
```

Selection uses required SGER/PACK inclusion followed by deterministic
source-kind quantile selection across early/middle/recent candidate dates with
ticker diversity. No selection was changed after lookup results.

## Alternate official-source result

The only provider path used was the official IDX listed-company announcement
endpoint:

```text
https://www.idx.co.id/primary/ListedCompany/GetAnnouncement
```

There were exactly eight event-specific requests, one per selected event. All
returned HTTP 403 with retained HTML response bytes and SHA-256. No attachment
was fetched because no announcement payload was available; no KSEI retry and no
issuer URL was guessed or queried.

```text
RESOLVED_EXACT                                  = 0
OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT   = 0
OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS       = 0
OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE = 0
NO_ALTERNATE_OFFICIAL_DOCUMENT_DISCOVERED       = 0
PROVIDER_DISCOVERY_FAILURE                      = 8
```

The accepted semantic remains explicit `REGULAR_MARKET_EX_DATE`; no candidate,
cum, record, distribution, listing, publication, exercise, or next-session
date was promoted to a transition.

The hardened path is fail-closed. The V14 manifest and all 14 of its
hash-bound outputs were verified. The V2 execution manifest and all 18 of its
hash-bound outputs were verified. A successful API page is usable only when
`ResultCount` equals `Replies` within the requested page size; absent or
truncated pagination evidence is a provider failure. A document can resolve
only when its official URL and SHA are valid, its ticker and rights semantics
match, every retained target date and ratio matches, and its attachment URL is
associated with exactly one selected economic event. Naked ticker/date or
`LINKED_EXACT` labels are not accepted.

Separate path assessment:

```text
IDX_RIGHTS_DOCUMENT_PATH     = ALTERNATE_OFFICIAL_PATH_NOT_RELIABLY_REPEATABLE
ISSUER_RIGHTS_DOCUMENT_PATH  = NOT_TESTED_IN_BOUNDED_PILOT
ALTERNATE_RIGHTS_SOURCE_CAPABILITY = ALTERNATE_OFFICIAL_PATH_PARTIAL
```

The aggregate remains `PARTIAL`, not a universe-wide failure, because issuer
IR/disclosure path was not tested. The IDX endpoint's uniform 403 results do
not establish historical negative authority or historical completeness.

## Linkage and reconciliation

The full V14 source/linkage inputs were independently recomputed in the audit
logic. No official document was retained, so no new pair evidence existed:

```text
PRIOR_PROVEN_LINKAGES       = 27
RECOMPUTED_PROVEN_LINKAGES  = 27
NEW_PROVEN_LINKAGES         = 0
REMOVED_OR_CONFLICTING      = 0
```

No reconciliation successor was necessary. V14 remains controlling:

```text
SOURCE_EVIDENCE_ROWS = 412
CROSS_SOURCE_COLLAPSES = 22
SAME_SOURCE_COLLAPSES = 3
ECONOMIC_EVENTS = 387
RESOLVED = 160
UNRESOLVED = 181
NON_BASIS = 46
RIGHTS_HMETD_UNRESOLVED = 68
```

Pilot geometry:

```text
RIGHTS_UNRESOLVED_BEFORE = 68
RIGHTS_PILOT_TESTED = 8
RIGHTS_PILOT_RESOLVED = 0
RIGHTS_NEW_LINKAGES = 0
RIGHTS_UNRESOLVED_AFTER = 68
remaining untested rights events = 60
```

## Authority, scientific state, and validation

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN

DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

Validation on the final lane HEAD:

```text
focused alternate/economic tests = PASS (28/28)
CA/integrity suite = PASS (131/131)
full pytest = PASS (403/403)
compileall = PASS
git diff --check = PASS
artifact hash validation = PASS (zero mismatches)
deterministic assessment replay = PASS (V4 derived from V2 without provider calls)
exact-head CI = PASS, run 33309931493, head 117274b8cfac6bf23577cfe30d9bdd11936f6077, pytest job 2m41s
```

The exact-head run emitted one GitHub deprecation annotation covering
`actions/checkout@v4` and `actions/setup-python@v5` (Node.js 20 on Node.js 24),
plus the normal Node deprecation output in the job log. These are warnings,
reported separately from the successful test result.

This checkpoint stops after the bounded pilot and is returned for ChatGPT
review. Full residual RIGHTS acquisition remains on hold pending a separately
authorized issuer-official path audit. V4 is the controlling result; V2/V3 are
historical immutable intermediates only.

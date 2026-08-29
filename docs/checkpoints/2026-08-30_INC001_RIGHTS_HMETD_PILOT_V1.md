# INC-001 bounded RIGHTS_HMETD pilot — V1

Date: 2026-08-30
Lane: `data/ca-aware-feature-basis-remediation-v1`
Controlling predecessor implementation HEAD: `05940cf1ec92a4a5f2159bd4080f60e1d7e254b4`

This checkpoint records one bounded, outcome-blind source-capability pilot. It
does not authorize or perform Phase-E, provider bulk acquisition, outcome or
target access, model fit/refit/scoring, counter mutation, canonical historical
rewrite, production execution, or merge of PR #103/#108.

## Controlling inputs and immutable outputs

The controlling V9 reconciliation input remains unchanged:

```text
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v9-stock-split-linkage-correction-final
MANIFEST SHA-256: dcc5e05ca3bc5fe7da148629a26fb913a6e85b92a88cbc88180cfde05eec30cc
```

The new bounded acquisition root is:

```text
D:\Documents\Project\idx-ca-rights-hmetd-pilot-20260830-v1
MANIFEST SHA-256: 4f40cbc99457978f72a4333edbf734b59d09bb7a71586e6922f37c3a085bf24a
```

The new post-pilot reconciliation root is:

```text
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v10-rights-pilot
MANIFEST SHA-256: 62b87ee76feb1076bf92d03a055ae3ed56a754178cd5cecb3338646a1cba892b
```

Its deterministic frozen-byte rerun is:

```text
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v10-rights-pilot-rerun
```

All 61 non-manifest files were byte-identical between the controlling V10 root
and its rerun. V9, R3, R3.1, and all prior roots remain immutable and are not
overwritten.

## Selection and bounded official-source result

The pilot loader read exactly 71 rows from the V9 economic-event ledger where
`economic_family=RIGHTS_HMETD` and `transition_status=UNRESOLVED`. The 71
economic events have 71 source representations. Selection was persisted before
provider lookup:

```text
PILOT_TESTED                 = 12
IDX_GET_ISSUED_HISTORY      = 6
KSEI_REGISTERED_SECURITY_HISTORY = 6
unique tickers               = 12
temporal strata              = EARLY / MIDDLE / RECENT
```

Selected tickers were `SMCB, VICO, TBLA, BBYB, BABY, BNBR, SAME, SGER,
MMIX, GMFI, PACK, MPPA`. The candidate audit produced no accepted linkage:
date proximity remains `POSSIBLE_SAME_EVENT` only and cannot promote identity.

The one bounded provider pass made 12 KSEI monthly index requests and 12 exact
IDX event requests. No exact official document was fetched because the KSEI
index returned no matching candidate document rows. No request was retried.

```text
RESOLVED_EXACT                                  = 0
OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE = 6
NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED           = 6
OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT   = 0
OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS       = 0
PROVIDER_DISCOVERY_FAILURE                      = 0
NEW_LINKAGES                                    = 0
```

The six IDX rows establish bounded official event evidence only; they do not
establish the regular-market Ex date. The six KSEI results are not historical
negative authority. The post-pilot source-path verdict is
`PARTIAL_HISTORICAL_CAPABILITY`, with historical completeness explicitly not
established.

The accepted transition contract remains the explicit official schedule
semantic `Tanggal Ex di Pasar Regular/Reguler dan Pasar Negosiasi`. Candidate,
Cum, Record, Distribution, listing, exercise, and next-session dates are not
substitutes for that semantic.

## Reconciled counts and linkage audit

V10 re-ran the existing fail-closed reconciler over all source rows and all V9
adjudications/linkages/transitions, adding no pilot transition or linkage:

| Metric | V9 | V10 post-pilot | Delta |
|---|---:|---:|---:|
| Source evidence rows | 412 | 412 | 0 |
| Cross-source collapses | 22 | 22 | 0 |
| Same-source collapses | 3 | 3 | 0 |
| Economic events | 387 | 387 | 0 |
| Resolved transitions | 157 | 157 | 0 |
| Unresolved transitions | 184 | 184 | 0 |
| Non-basis exclusions | 46 | 46 | 0 |

```text
PRIOR_PROVEN_LINKAGES       = 27
RECOMPUTED_PROVEN_LINKAGES  = 27
NEW_PROVEN_LINKAGES         = 0
REMOVED_OR_CONFLICTING      = 0
```

Rights geometry remains exactly 71 unresolved economic events. The V10 root
preserves the full 291-event future plan, with capability-verification requests
separate from later bulk acquisition:

```text
baseline unresolved physical events = 291
capability-verification requests    = 24
later bulk-acquisition requests     = 13
bulk acquisition executed           = FALSE
```

## Scientific state and validation

The scientific verdict is unchanged:

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

Validation on this lane:

```text
focused RIGHTS_HMETD pilot tests = PASS
CA/integrity suite (13 modules)  = PASS
full pytest                       = PASS (exit 0, 100% completion)
compileall                        = PASS
git diff --check                  = PASS
artifact hash/conservation audit = PASS
deterministic comparison         = PASS (61/61 non-manifest files identical)
```

This checkpoint is complete and returned for ChatGPT review. Push this lane
after the final Git review. Do not merge PR #108/#103 and do not perform any
further production or scientific execution.

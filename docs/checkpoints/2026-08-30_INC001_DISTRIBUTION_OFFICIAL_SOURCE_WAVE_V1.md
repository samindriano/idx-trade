# INC-001 bounded official distribution-source wave — V1

Date: 2026-08-30 Asia/Jakarta
Lane: `data/ca-aware-feature-basis-remediation-v1`
Scope: exactly 18 unresolved V14 economic events: `BONUS_SHARES` 11 and `STOCK_DIVIDEND` 7

## Controlling inputs and acquisition boundary

The controlling predecessor remains immutable V14:

```text
ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v14-same-exact
MANIFEST SHA-256 = c095c00c31691c07cbf4d50c447abafde9b00db0e93f8184ea6e9a83b4a1990b
SOURCE_EVIDENCE_ROWS = 412
ECONOMIC_EVENTS = 387
RESOLVED = 160
UNRESOLVED = 181
NON_BASIS = 46
PROVEN_LINKAGES = 27
```

The retained-evidence triage input was:

```text
ROOT = D:\Documents\Project\idx-ca-retained-evidence-triage-20260830-v1
MANIFEST SHA-256 = 0422948682e849022bc31ff0c93e0029e7a4db5f66566cf0e2a69d65ad6bdd86
```

One bounded official-source wave was executed only for the 18 selected
`BONUS_SHARES` and `STOCK_DIVIDEND` events. It used 16 KSEI monthly index
requests (the official `share-bonus` / `share-dividend` paths), 16 exact-date
IDX `GetIssuedHistory` requests for the 16 IDX-sourced targets, and downloaded
5 official KSEI documents exposed by those indexes. No generic provider,
market provider, broad crawl, URL permutation, retry, or alternate family was
used. No provider was called during the offline correction or reconciliation.

The controlling acquisition artifact is:

```text
ROOT = D:\Documents\Project\idx-ca-official-distribution-acquisition-20260830-v4-final
MANIFEST SHA-256 = 33297117036972e91609f635175a3cce88aeada6a94b0c637edf1cf81a700c0d
```

Earlier local v1–v3 derivation roots are superseded correction history only;
v4 is the controlling artifact. Raw official response bytes were preserved and
the final v4 manifest verifies every output. The official document URL and
SHA-256 are bound in the final evidence table.

## Per-event result

```text
RESOLVED_EXACT                                      = 3
OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT      = 0
OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS          = 0
OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE = 5
NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED               = 5
PROVIDER_DISCOVERY_FAILURE                          = 5
NOT_ATTEMPTED_DUE_TO_CONFIRMED_PATH_FAILURE        = 0
TOTAL                                                = 18
```

The three exact results are all `BONUS_SHARES` and use the accepted semantic
`REGULAR_MARKET_EX_DATE`:

```text
KLAS  candidate 2024-11-29 -> regular-market Ex 2024-11-11
     https://web.ksei.co.id/Announcement/Files/173370_ksei_24898_jku_1024_202411061740.pdf
     SHA-256 1dd935ee2ca7ed2e4c5a90bf9a20d4a159461484c2b4ff045e8e88337fc7f0ea

UFOE  candidate 2024-12-24 -> regular-market Ex 2024-12-04
      https://web.ksei.co.id/Announcement/Files/174077_ksei_27586_jku_1124_202411291640.pdf
      SHA-256 2e9b08c2ba1eca82678a9528e6144fc906d3257e1a078a78fad5e115bc3b2719

CLEO  candidate 2025-06-30 -> regular-market Ex 2025-06-10
      https://web.ksei.co.id/Announcement/Files/181030_ksei_13164_jku_0625_202506031629.pdf
      SHA-256 6bb0f8eabdf878211794bdec9b622172d8bcac560dbc5fc9fa634d8d07b613cd
```

The 15 unresolved events are `BONUS_SHARES` 8 and `STOCK_DIVIDEND` 7. The
five provider failures are discovery failures, not negative authority. The
five document-unavailable results have positive official IDX event evidence
but no exact transition document exposed by the bounded paths. Candidate,
cum, record, distribution, payment, listing, issued-share, and next-session
dates were never promoted to transition authority. CNMA and MEJA were not
resolved merely by reaccepting their retained mechanics.

## Reconciliation successor

Because three exact transition attestations were newly proven, the existing
fail-closed reconciler produced one successor:

```text
ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v15-distribution-wave
MANIFEST SHA-256 = d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025
```

```text
BEFORE V14 = 412 source / 387 economic / 160 resolved / 181 unresolved / 46 non-basis / 27 linkages
AFTER  V15 = 412 source / 387 economic / 163 resolved / 178 unresolved / 46 non-basis / 27 linkages
DELTA      =   0 source /   0 economic /   3 resolved /  -3 unresolved /  0 non-basis /  0 linkages
```

Only the three new source-bound transition attestations were added. The
source-evidence ledger hash is unchanged:

```text
V14 and V15 source_evidence_ledger.csv SHA-256 = edd7ef441db3e7652639ab8914580334b7800b759683d05eaeaae5710237e7a7
```

No same-event linkage was added, removed, or altered. V15 is not a scientific
admission and does not rewrite canonical historical prices or runtime state.

## Validation and integrity state

```text
ACQUISITION_TARGET_ID_CONSERVATION = PASS (18/18; 11 BONUS_SHARES + 7 STOCK_DIVIDEND)
OFFICIAL_RAW_RESPONSE_HASHES        = PASS (manifest verified)
OFFICIAL_DOCUMENT_BYTES_AND_HASHES  = PASS (5/5)
V14_INPUT_MANIFEST                  = PASS
SOURCE_LEDGER_BYTE_HASH             = PASS (unchanged)
RECONCILIATION_INVARIANTS            = PASS
DETERMINISTIC_RECONCILIATION_REPLAY = PASS
NEW_TRANSITION_ATTESTATIONS         = PASS (3/3; accepted semantic/ref/SHA)
NEW_LINKAGES                        = 0
```

The following remain unchanged and fail closed:

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

No outcomes, targets, Phase-E, model, refit, score, IC/Sharpe, counter,
PaperState, production, backfill, or merge action occurred. No application,
runtime, or science source code changed.

## Next action

Park V15 for review. Any further acquisition for the 15 unresolved events must
be separately authorized only after reviewing the five provider failures and
the five document-unavailable paths; do not retry this wave or infer negative
historical authority from its gaps.

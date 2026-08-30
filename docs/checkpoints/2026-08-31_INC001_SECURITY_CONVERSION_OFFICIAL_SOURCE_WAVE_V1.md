# INC-001 bounded official security-conversion source wave — V1

Date: 2026-08-31 Asia/Jakarta
Lane: `data/ca-aware-feature-basis-remediation-v1`
Scope: exactly the four current V15 unresolved `TRUE_SECURITY_CONVERSION` events

## Controlling state and boundary

The controlling reconciliation remains:

```text
ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v15-distribution-wave
MANIFEST SHA-256 = d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025
SOURCE_EVIDENCE_ROWS = 412
ECONOMIC_EVENTS = 387
RESOLVED = 163
UNRESOLVED = 178
NON_BASIS = 46
PROVEN_LINKAGES = 27
TRUE_SECURITY_CONVERSION_UNRESOLVED = 4
```

The pass used exactly four event-specific official requests: three exact-date
IDX `GetIssuedHistory` requests for `ASSA`, `KAEF`, and `PACK`, and one KSEI
registered-security history request for `MFIN`. Retained official IDX bytes
were preserved for the existing `ASSA`, `KAEF`, and `PACK` evidence, including
the positive `PACK` event record whose new exact-date response was empty. No
retry, URL permutation, generic provider, broad crawl, alternate family, or
market-provider call was used.

The controlling acquisition artifact is:

```text
ROOT = D:\Documents\Project\idx-ca-official-security-conversion-acquisition-20260830-v2
MANIFEST SHA-256 = 108e89f5145364ae1e348e8c8baec9ca5035b4f5e8f7821ff84531b387224f11
```

The earlier v1 artifact is superseded derivation history because its parser
did not normalize the IDX label `Obligasi Wajib Konversi` and misaligned an
empty KSEI Cum Date cell. V2 corrects both issues and verifies every output
hash.

## Per-event result

```text
RESOLVED_EXACT                                      = 0
OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT      = 1
OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS          = 0
OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE = 3
NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED               = 0
PROVIDER_DISCOVERY_FAILURE                          = 0
TOTAL                                                = 4
```

```text
ASSA  -> OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE
      Exact official IDX event record is present; no source/receiving mechanics
      or exact old/new trading-basis transition document is exposed.

KAEF  -> OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE
      Exact official IDX event record is present; no source/receiving mechanics
      or exact old/new trading-basis transition document is exposed.

PACK  -> OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE
      Retained official IDX event record is present; the bounded new exact-date
      request returned an empty result, and no transition document is exposed.

MFIN  -> OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT
      KSEI proves `1 MFIN : .052401 ADMF` mechanics and identity, with record
      date 2025-09-30 and distribution date 2025-10-01. It does not state an
      accepted effective conversion / first-new-basis / old-last-basis boundary.
```

The accepted conversion transition semantic is therefore absent for all four.
Record, distribution, candidate, settlement, exercise, generic conversion,
and next-session dates were not promoted to transition authority.

## Linkage and reconciliation

```text
PRIOR_PROVEN_LINKAGES       = 27
RECOMPUTED_PROVEN_LINKAGES  = 27
NEW_PROVEN_LINKAGES         = 0
REMOVED_OR_CONFLICTING      = 0
```

No new exact transition or duplicate source representation was proven. V15
remains controlling and no no-op successor was created:

```text
BEFORE = 412 / 387 / 163 / 178 / 46 / 27
AFTER  = 412 / 387 / 163 / 178 / 46 / 27
```

The source-evidence ledger and all global admission blockers remain unchanged.

## Validation and blockers

```text
V15_INPUT_MANIFEST                  = PASS
TARGET_CONSERVATION                 = PASS (4/4; ASSA, KAEF, MFIN, PACK)
OFFICIAL_REQUEST_LEDGER             = PASS (4 requests; all HTTP 200)
RETAINED_SOURCE_HASHES              = PASS
ACQUISITION_MANIFEST_OUTPUT_HASHES  = PASS (bad=0)
TRANSITION_ATTESTATIONS             = PASS (0 accepted; no false exact claim)
RECONCILIATION_COUNTS               = PASS (unchanged)
GIT_DIFF_CHECK                      = PASS
```

The following remain fail closed:

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

No application, runtime, science, model, outcome, target, counter, PaperState,
canonical historical data, production, backfill, or merge action occurred.

## Review handoff

Park V15 unchanged for ChatGPT review. Do not automatically proceed to
`MERGER` or `CAPITAL_RESTRUCTURING`. Any future source work requires a separate
bounded authorization; this pass must not be retried or used as negative
historical authority.

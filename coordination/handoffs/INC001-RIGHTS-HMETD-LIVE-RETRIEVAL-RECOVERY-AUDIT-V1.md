# Handoff: INC-001 RIGHTS_HMETD live-retrieval recovery audit V1

from: MAIN / `data/ca-aware-feature-basis-remediation-v1`
to: ChatGPT review
date: 2026-08-30

## Review decision requested

Review the bounded live source-contract audit and controlling V13
reconciliation. Do not merge PR #108 or PR #103. Do not start residual RIGHTS
acquisition from this handoff.

## Return values

```text
REMOTE_HEAD_AT_HANDOFF = 7a55753dace95a85d6abe182347877eda4bdb46d
MPPA_CANARY_LIVE_RESULT = HTTP_200_EXPECTED_CONTENT
ROOT_CAUSE_OF_PRIOR_HTTP500 = unresolved provider/application/request-context condition; exact transport cause not proven
SAME_SIX_KSEI_TARGETS = SAME, SGER, MMIX, GMFI, PACK, MPPA
LIVE_INDEX_SUCCESS_COUNT = 2
LIVE_INDEX_FAILURE_COUNT = 1
LIVE_INDEX_NONMATCHING_COUNT = 3
EXACT_DOCUMENTS_FOUND = 2
NEW_RESOLVED_EXACT = 1 (GMFI; MPPA was already retained)

RIGHTS_INDEX_SOURCE_CONTRACT_VERDICT = RIGHTS_INDEX_LIVE_CONTRACT_CONDITIONALLY_REPEATABLE

PRIOR_PROVEN_LINKAGES = 27
RECOMPUTED_PROVEN_LINKAGES = 27
NEW_PROVEN_LINKAGES = 0
REMOVED_OR_CONFLICTING = 0

ECONOMIC_EVENTS = 387
RESOLVED = 159
UNRESOLVED = 182
NON_BASIS = 46
RIGHTS_HMETD_UNRESOLVED = 69

FULL_RIGHTS_ACQUISITION_RECOMMENDATION = HOLD_FOR_ALTERNATE_SOURCE_PATH

ARTIFACT_ROOT = D:\Documents\Project\idx-ca-rights-hmetd-live-canary-20260830-v4-followup-parsed
MANIFEST_SHA256 = f83ec863afc9a3245b89aee3601af2e77cee1cd32e53c355d52987a3fb523dff

FOCUSED_TESTS = 10 passed
CA_INTEGRITY_TESTS = PASS (13 modules)
FULL_PYTEST = PASS (local, exit 0)
COMPILEALL = PASS
DIFF_CHECK = PASS
ARTIFACT_HASH_AUDIT = PASS (zero mismatches)
DETERMINISTIC_RECONCILIATION = PASS (68/68)
EXACT_HEAD_CI = PASS, run 33297919231, 386 passed, 5 warnings

DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

## Evidence and boundaries

The old V1 `masr` route is not a negative authority result. The corrected
route is proven compatible with retained MPPA evidence, but the six-target
live result is only conditionally repeatable: 2 row-found, 3 no-match, and 1
HTTP 500. The HTTP 500 cannot be assigned to a specific header/session/TLS
cause because retained transport metadata was not recorded.

New GMFI evidence is:

```text
KSEI-30122/JKU/1225
https://web.ksei.co.id/Announcement/Files/GMFI_RIGHT_20251223_ID.pdf
SHA256 = 5102179867d88237470a85be2cf1f4f755dfd0693d3c345650401a884b71409b
REGULAR_MARKET_EX_DATE = 2025-12-22
```

The official parser used the explicit regular-market Ex wording. No date
inference, source-pair linkage, historical completeness claim, or full
residual acquisition was made.

Controlling reconciliation:

```text
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v13-rights-gmfi-live
MANIFEST = 03ae8ed944f2e8a656305dceb3058f849c3b06c7f906a940144044e90b0baa97

D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v13-rights-gmfi-live-rerun
MANIFEST = 4ce462bba357a3a7e7b19d435da72e01e5f56784ffbbedce86fd69f2d3901c41
```

Stop for ChatGPT review. No further production or scientific execution is
authorized by this handoff.

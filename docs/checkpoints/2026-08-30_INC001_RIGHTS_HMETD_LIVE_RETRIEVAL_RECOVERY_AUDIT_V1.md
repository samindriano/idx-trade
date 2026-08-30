# INC-001 RIGHTS_HMETD live-retrieval recovery audit V1

date: 2026-08-30
lane: `data/ca-aware-feature-basis-remediation-v1`
scope: exactly the persisted six KSEI-origin targets from the prior 12-target pilot

## Decision

The old V1 request path was wrong for HMETD discovery: it queried the general
`/corporate-action-schedules/masr` route with `setLocale=en-US`. The corrected
route is `/corporate-action-schedules/rights-distribution` with
`setLocale=id-ID`, and it is source-contract compatible with the retained
successful MPPA observation.

The bounded live recovery was executed as one MPPA canary followed, because
the canary passed, by exactly one request for each of the other five persisted
KSEI targets. Exact PDF hrefs were fetched once only for MPPA and GMFI. No
remaining RIGHTS acquisition was performed.

## Current live evidence

The six targets and candidate routing windows were:

| ticker | candidate routing | live index result | document result |
|---|---|---|---|
| SAME | 2021-03 | `INDEX_SUCCESS_NO_MATCHING_ROW` | not fetched |
| SGER | 2024-05 | `INDEX_SUCCESS_NO_MATCHING_ROW` | not fetched |
| MMIX | 2025-10 | `PROVIDER_FAILURE` / HTTP 500 | not fetched |
| GMFI | 2025-12 | `INDEX_SUCCESS_DOCUMENT_ROW_FOUND` | PDF 200, parsed exact |
| PACK | 2026-01 | `INDEX_SUCCESS_NO_MATCHING_ROW` | not fetched |
| MPPA | 2026-06 | `INDEX_SUCCESS_DOCUMENT_ROW_FOUND` | PDF 200, parsed exact |

Counts across all six live index requests:

```text
LIVE_INDEX_SUCCESS_COUNT = 2
LIVE_INDEX_FAILURE_COUNT = 1
LIVE_INDEX_NONMATCHING_COUNT = 3
EXACT_DOCUMENTS_FOUND = 2
provider requests total = 8
  1 MPPA canary index
  5 remaining target indexes
  2 target PDFs (MPPA and GMFI)
```

The MPPA PDF is the already-known positive, with the same bytes and hash as
the retained evidence:

```text
KSEI-15669/JKU/0626
https://web.ksei.co.id/Announcement/Files/MPPA_RIGHT_20260629_ID.pdf
SHA256 = 8eda1cd7fbddf5344432c88660dc8b48319b711c848ff4ec85cd3b85b010f84e
accepted REGULAR_MARKET_EX_DATE = 2026-06-26
```

GMFI is new source-bound evidence:

```text
KSEI-30122/JKU/1225
https://web.ksei.co.id/Announcement/Files/GMFI_RIGHT_20251223_ID.pdf
SHA256 = 5102179867d88237470a85be2cf1f4f755dfd0693d3c345650401a884b71409b
accepted REGULAR_MARKET_EX_DATE = 2025-12-22
```

The PDF parser found the explicit source-native semantic
`Tanggal Ex di Pasar Regular dan Pasar Negosiasi`; no candidate, record,
distribution, listing, or next-session inference was used.

## Request-contract audit

Facts proven by retained request ledgers and current source code:

| field | prior V1 | corrected/live | retained successful MPPA |
|---|---|---|---|
| path | `.../masr` | `.../rights-distribution` | `.../rights-distribution` |
| query order | `Month,Year,setLocale` | `Month,Year,setLocale` | `Month,Year,setLocale` |
| Month | two digits | two digits | two digits |
| Year | four digits | four digits | four digits |
| locale | `en-US` | `id-ID` | `id-ID` |
| method | GET by `urllib.request.Request` default | GET | not recorded |
| request headers | only explicit User-Agent in current runner | same | not recorded |
| cookies/session | no explicit session/cookie | same | not recorded |
| compression | no explicit Accept-Encoding | same | not recorded |
| TLS | default urllib HTTPS context | same | not recorded |
| redirects | default urllib redirect handler | same | final URL only |

The exact cause of the earlier corrected HTTP 500 is not proven. The corrected
V2 MPPA request and retained successful MPPA request have the same route,
query, and locale, while retained evidence lacks transport metadata. The
bounded conclusion is an unresolved provider/application/request-context
condition; the HTTP 500 is not historical absence and cannot be attributed
specifically to TLS, compression, cookies, headers, or redirects.

## Source-contract verdict and acquisition decision

```text
RIGHTS_INDEX_SOURCE_CONTRACT_VERDICT = RIGHTS_INDEX_LIVE_CONTRACT_CONDITIONALLY_REPEATABLE
FULL_RIGHTS_ACQUISITION_RECOMMENDATION = HOLD_FOR_ALTERNATE_SOURCE_PATH
```

The route produced two target rows and two 200 PDFs, but also three valid
no-match responses and one HTTP 500 across the six target windows. This is not
sufficient evidence for a full residual acquisition. The prior V1 `masr`
result remains an old wrong-path observation, not a negative authority claim.

## Reconciliation

The new GMFI PDF is source-bound and adds one exact pilot transition. MPPA is
duplicate evidence of the already-retained exact document, so it adds no new
transition. The normal fail-closed reconciler produced:

```text
                         V12 prior   V13 controlling   delta
source evidence rows          412          412            0
cross-source collapses         22           22            0
same-source collapses           3            3            0
economic events               387          387            0
resolved transitions          158          159           +1
unresolved transitions        183          182           -1
non-basis exclusions            46           46            0
```

```text
PRIOR_PROVEN_LINKAGES       = 27
RECOMPUTED_PROVEN_LINKAGES  = 27
NEW_PROVEN_LINKAGES         = 0
REMOVED_OR_CONFLICTING      = 0
RIGHTS_HMETD_UNRESOLVED     = 69
```

No heuristic or date-proximity linkage was introduced.

## Immutable artifacts

Raw live follow-up and parsed controlling audit:

```text
D:\Documents\Project\idx-ca-rights-hmetd-live-canary-20260830-v3-bounded-followup
MANIFEST = 0ddcab18d0092f28cfdd73eddf7dc91d6cfdb5abd7dc5492e4d74024e197a837

D:\Documents\Project\idx-ca-rights-hmetd-live-canary-20260830-v4-followup-parsed
MANIFEST = f83ec863afc9a3245b89aee3601af2e77cee1cd32e53c355d52987a3fb523dff
```

Pilot and controlling reconciliation:

```text
D:\Documents\Project\idx-ca-rights-hmetd-pilot-20260830-v4-gmfi-live
MANIFEST = e233e2d328ab1307b699db8fab850151e0e8a25bf28af36ed8998887277109e3

D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v13-rights-gmfi-live
MANIFEST = 03ae8ed944f2e8a656305dceb3058f849c3b06c7f906a940144044e90b0baa97

D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v13-rights-gmfi-live-rerun
MANIFEST = 4ce462bba357a3a7e7b19d435da72e01e5f56784ffbbedce86fd69f2d3901c41
```

All listed output hashes validated with zero mismatches. Deterministic local
reconciliation comparison passed for `68/68` compared files.

## Authority and scientific state

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY             = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY                = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY  = UNKNOWN

DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

## Validation and repository state

```text
focused RIGHTS/canary tests = 10 passed
CA/integrity suite           = PASS (13 modules)
full pytest                  = PASS (local, exit 0)
compileall                   = PASS
git diff --check             = PASS
artifact hash validation     = PASS (zero mismatches)
deterministic reconciliation = PASS (68/68)
exact-head CI on implementation commit = PASS, run 33297740347, 386 passed, 5 warnings
exact-head CI on handoff commit        = PASS, run 33297919231, 386 passed, 5 warnings
```

Implementation and handoff commits:

```text
data/ca-aware-feature-basis-remediation-v1
bf87482d3746c5f92bcd05741ed17683d8a12c62
7a55753dace95a85d6abe182347877eda4bdb46d
```

The branch is pushed and clean. PR #108 remains OPEN/DRAFT/unmerged. No
production execution, Phase-E, outcomes/targets, model work, counter
mutation, canonical rewrite, or merge was performed.

This checkpoint is ready for ChatGPT review. Stop here.

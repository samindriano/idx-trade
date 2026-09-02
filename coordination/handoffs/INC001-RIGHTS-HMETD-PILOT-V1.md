# Handoff: INC-001 bounded RIGHTS_HMETD pilot V1

from: MAIN / `data/ca-aware-feature-basis-remediation-v1`
to: ChatGPT review
date: 2026-08-30
scope: bounded source-capability verification only

## Review pins

```text
branch: data/ca-aware-feature-basis-remediation-v1
pre-pilot HEAD: 05940cf1ec92a4a5f2159bd4080f60e1d7e254b4
controlling V9 manifest: dcc5e05ca3bc5fe7da148629a26fb913a6e85b92a88cbc88180cfde05eec30cc
pilot acquisition manifest: 4f40cbc99457978f72a4333edbf734b59d09bb7a71586e6922f37c3a085bf24a
post-pilot V10 manifest: 62b87ee76feb1076bf92d03a055ae3ed56a754178cd5cecb3338646a1cba892b
```

## Result to accept/reject

The exact 71-event unresolved RIGHTS_HMETD scope was loaded from V9. A
deterministic selection of 12 events was persisted before lookup: six IDX and
six KSEI, with early/middle/recent coverage and 12 unique tickers. One bounded
no-retry official-source pass was performed.

```text
pilot tested                  = 12
pilot resolved exact          = 0
event evidence/no doc         = 6
no official document found    = 6
new same-event linkages       = 0
rights unresolved after pilot = 71
source capability verdict     = PARTIAL_HISTORICAL_CAPABILITY
```

No direct official rights schedule with the accepted regular-market Ex semantic
was retained for this sample. The six IDX event rows are not transition
authority. The KSEI index results are not negative historical authority. No
document was fetched, and no request was retried.

The full V10 reconciliation remained unchanged from V9: 412 source rows, 22
cross-source collapses, 3 same-source collapses, 387 economic events, 157
resolved transitions, 184 unresolved transitions, and 46 non-basis exclusions.
Linkages are 27 prior / 27 recomputed / 0 new / 0 removed-conflicting.

The baseline plan remains exactly 291 unresolved physical event identities,
with 24 capability-verification requests and 13 later bulk-acquisition
requests. The pilot is not bulk acquisition and does not consume that later
authorization.

## Files changed in this handoff

- `scripts/acquire_inc001_rights_hmetd_pilot_v1.py`
- `scripts/build_inc001_rights_hmetd_pilot_reconciliation_v1.py`
- `tests/test_inc001_rights_hmetd_pilot_v1.py`
- `docs/checkpoints/2026-08-30_INC001_RIGHTS_HMETD_PILOT_V1.md`
- `coordination/handoffs/INC001-RIGHTS-HMETD-PILOT-V1.md`

## Boundaries

```text
Phase-E                         = NOT RUN
outcomes/targets                = NOT ACCESSED
fit/refit/score                 = NOT RUN
counter mutation                = NONE
canonical historical rewrite    = NONE
production execution            = NONE
PR #103/#108 merge              = NONE
```

The scientific state remains `DATA_ADMISSION=FAIL`,
`RESEARCH_ADMISSION=FAIL`, `MODEL_PROMOTION=NOT_EVALUATED`,
`HISTORICAL_APPLICATION=BLOCKED_PHASE_E_NOT_RUN`, `REFIT_AUTHORIZED=FALSE`,
`COUNTER_ACTION=NONE`.

## Required review decision

Review the two immutable roots and the deterministic rerun. If accepted, the
next action must be separately authorized; this handoff does not authorize
full 71-event rights acquisition, other CA acquisition, Phase-E, model work,
counter action, production, or merge. Stop here after ChatGPT review.

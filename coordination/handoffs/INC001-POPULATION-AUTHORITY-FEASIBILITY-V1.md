# INC-001 Population Authority Feasibility V1 Handoff

Date: 2026-08-31 Asia/Jakarta
Lane: `data/ca-aware-feature-basis-remediation-v1`
HEAD: `488f2ca3a9b07ad182bf17e113c90f4f59dbb538`

## Decision

`INC001_POPULATION_AUTHORITY_FEASIBILITY=COMPLETE`

`HISTORICAL_ADMISSION=BLOCKED_ON_POPULATION_AUTHORITY_AND_UNRESOLVED_TRANSITION_SEMANTICS`

`KNOWN_EVENT_CLOSURE_RED_TEAM=PASS_WITH_NONBLOCKING_FINDINGS`

The retained event-remediation work is materially complete and the remaining
long tail is parked fail-closed. The prior “population authority is sole
blocker” wording is narrowed: 178 V16 transition semantics remain unresolved,
and the existing gate requires `structural_event_complete` in addition to
population and temporal authority.

## Immutable evidence

Primary artifact root:

`D:\Documents\Project\idx-ca-inc001-population-authority-feasibility-20260831-v1`

Primary artifact `MANIFEST.json` SHA-256:

`89911c0ea1cd14f5c6dad771214f0fb2f6b4873afaae65541ab10329855c0145`

Bound input manifests:

- V16 composite reconciliation: `3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030`;
- closure feasibility: `42a1e20f29ef4028ecfaae99f032dd138511c6fd1bf5242c66c057683cc4172c`;
- R3.1 geometry: `9075b707db70cf7e2a6fce4b504bfdf8c16369b9de75420f90d9808f1b994c2b`;
- retained source-authority V8: `556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71`;
- merger bounded artifact: `747c83ac3bcf6dac15e73c1e71553a0ae80422b9da0f25deb57b3139dceff6c1`;
- capital bounded artifact: `a4f4fd188d830088cdafbb1bbcd5716ae1f92cc6fcd8314181cf9dbefa832887`.

## Exact results

- V16 event census: 387 total; 163 `RESOLVED`, 178 `UNRESOLVED`, 46
  `NOT_APPLICABLE_NON_BASIS`;
- current gate: `FAIL_STRUCTURAL_CA_COVERAGE_NOT_CERTIFIED`;
- R3.1 fit/application/closure: 240,344 / 276,153 / 365,968 rows;
- R3.1 fit/application/closure: 629 / 716 / 716 tickers;
- cross-section-only: 35,809 rows / 274 tickers;
- retained KSEI ticker presence: 610 / 716;
- population completeness: `UNKNOWN`;
- historical as-of authority: `UNKNOWN`;
- IDX negative authority: `UNSUPPORTED`;
- KSEI complete-interval authority: `UNKNOWN`;
- same-science certifiable subset: none established;
- prospective: conditionally possible, not currently proven.

## Guardrails

No provider/data acquisition, credentials, outcomes/targets, model/refit/score,
counter/PaperState/R2, canonical rewrite, production execution, backfill,
deploy, or merge occurred. No source/runtime/science implementation was
changed; only this audit builder and the two audit documents were added.

## Next decision for review

Do not infer safe rows from absence. If the closure is revisited, obtain one
authoritative source contract covering population-wide complete interval,
explicit no-event, historical as-of, revision semantics, and transition
identity; bind it to the existing fail-closed gate and V16 census before any
admission. Stop for independent review.

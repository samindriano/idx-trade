# INC-001 Population and Historical-As-Of Feasibility V2 Handoff

Date: 2026-08-31 Asia/Jakarta
Lane: `data/ca-aware-feature-basis-remediation-v1`
Audit tree: `c14e00e6b432705babe5e140b802b82031d7b880`

## Verdict

`FEASIBILITY_VERDICT=NO_CERTIFIABLE_SCOPE_CURRENTLY`

Full historical application/dependency scope is `NO-GO`: 716 application and
closure tickers, 276,153 application rows, and 365,968 closure rows remain
without certified population completeness or historical-as-of authority.

The two natural KSEI-derived candidates are also `NO-GO`:

- KSEI-present: 610 tickers, 267,002 application rows, 347,197 closure rows;
  population authority remains `UNKNOWN` for every ticker.
- KSEI ticker-certified: 567 tickers, 246,026 application rows, 320,448
  closure rows; population authority remains `UNKNOWN` for every ticker.

The feasibility requirements artifact records all 716 rows as
`OBSERVED_DEPENDENCY_GEOMETRY_ONLY` and
`NO_SAME_SCIENCE_CERTIFIABLE_SUBSET_ESTABLISHED`. R3.1 reports
`date_level_attestation=False` for all three required scopes. Resolved V17
transition rows are event evidence, not a population definition.

Read-only verification passed `21/21`, including controlling manifest hashes,
scope counts, authority states, R3 attestations, source-capability limits, and
V16/V17 population conservation.

## Evidence

- Feasibility manifest:
  `89911c0ea1cd14f5c6dad771214f0fb2f6b4873afaae65541ab10329855c0145`
- R3.1 manifest:
  `9075b707db70cf7e2a6fce4b504bfdf8c16369b9de75420f90d9808f1b994c2b`
- V16 manifest:
  `3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030`
- V17 manifest:
  `8d2139c9388c6b94c4131ca692f0de3add433c294e4a7b20f2db6d7f22b106e8`
- Source-authority V8 manifest:
  `556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71`

Current gate result remains
`FAIL_STRUCTURAL_CA_COVERAGE_NOT_CERTIFIED`. V17 preserves the V16 event,
source-row, linkage, and non-basis populations while promoting four transition
dispositions; it does not certify population or temporal authority.

## Boundaries

This audit is read-only and outcome-blind. No adapter, runtime/science code,
admission state, provider, production state, counter/PaperState/R2, deployment,
backfill, or Actions rerun was changed. Do not reopen historical admission or
construct a subset until the required authoritative source contract exists and
is bound to the existing fail-closed gate.

# INC-001 Population and Historical-As-Of Feasibility V2

Date: 2026-08-31 Asia/Jakarta
Repository: `samindriano/idx-trade`
Lane: `data/ca-aware-feature-basis-remediation-v1`
Audit tree: `c14e00e6b432705babe5e140b802b82031d7b880`
Mode: read-only, outcome-blind

## Decision

`FEASIBILITY_VERDICT=NO_CERTIFIABLE_SCOPE_CURRENTLY`

The full historical application/dependency scope is not certifiable. No
narrower ticker subset is currently established as scientifically valid under
the frozen V4 contract. Population completeness and historical-as-of authority
remain `UNKNOWN`; the existing admission gate remains blocked.

This is a feasibility decision, not an admission decision. No adapter,
runtime code, frozen science, or admission state was changed.

## Read-only verification

`FEASIBILITY_HARNESS=21 PASSED / 21`

The harness verified the four controlling manifest hashes, feasibility status
and subset verdict, all 716 dependency rows and their `UNKNOWN` authority,
KSEI status counts, all three R3 scope attestations, the IDX/KSEI/Security
Master authority limitations, V16/V17 population conservation, four-only V17
promotions, and V17's forbidden-action flags.

## Controlling evidence

- Feasibility artifact:
  `D:\Documents\Project\idx-ca-inc001-population-authority-feasibility-20260831-v1`
  manifest SHA-256:
  `89911c0ea1cd14f5c6dad771214f0fb2f6b4873afaae65541ab10329855c0145`
- R3.1 dependency artifact manifest SHA-256:
  `9075b707db70cf7e2a6fce4b504bfdf8c16369b9de75420f90d9808f1b994c2b`
- V16 controlling reconciliation manifest SHA-256:
  `3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030`
- V17 residual certification manifest SHA-256:
  `8d2139c9388c6b94c4131ca692f0de3add433c294e4a7b20f2db6d7f22b106e8`
- Source-authority V8 manifest SHA-256:
  `556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71`

V16 remains immutable. V17 changed only four existing transition dispositions:
167 resolved / 174 unresolved, versus V16's 163 resolved / 178 unresolved;
the 387-event, 412-source-row, 46-non-basis, and 27-linkage populations were
conserved. Transition certification does not establish population completeness
or historical-as-of authority.

## Scope feasibility matrix

| Candidate scope | Tickers | Application rows | Closure rows | Population authority | Result |
| --- | ---: | ---: | ---: | --- | --- |
| Full application/dependency closure | 716 | 276,153 | 365,968 | `UNKNOWN` for all 716 | `NO-GO` |
| KSEI-present ticker subset | 610 | 267,002 | 347,197 | `UNKNOWN` for all 610 | `NO-GO` |
| KSEI ticker-certified subset | 567 | 246,026 | 320,448 | `UNKNOWN` for all 567 | `NO-GO` |
| Tickers with resolved V17 transitions | Not a population scope | Not applicable | Not applicable | Transition evidence only | Not certifiable |

The feasibility requirements artifact contains 716 ticker rows. Every row is
`population_ca_authority=UNKNOWN` and
`identity_geometry_status=OBSERVED_DEPENDENCY_GEOMETRY_ONLY`. KSEI presence is
not an interval-complete, explicit-no-event, or historical-as-of authority.

The R3.1 reconciliation independently reports, for `EXACT_FINAL_FIT`,
`CROSS_SECTION_APPLICATION`, and `BACKWARD_DEPENDENCY_CLOSURE`,
`date_level_attestation=False` and
`UNKNOWN_TICKER_ONLY_NO_DATE_ATTESTATION`. Therefore removing absent or
unresolved KSEI tickers does not produce a certified subset.

Post-hoc exclusion is also not a same-science reduction: V4 cross-sectional
ranks and market context are computed across the full primary-liquid
application population. Exclusion changes the frozen population, support
geometry, and derived features. The retained feasibility artifact records
`NO_SAME_SCIENCE_CERTIFIABLE_SUBSET_ESTABLISHED`.

## Authority findings

- IDX category queries provide only a partial positive result set; category
  unions omitted 498 rows from the comparable broad result and do not provide
  an atomic historical universe.
- IDX explicit exhaustive no-event authority is `UNSUPPORTED`; an empty query
  is not a negative row.
- KSEI pages support parsed positive facts only. Pagination completeness,
  observed-through/as-of, global universe, absence semantics, and complete
  interval/no-event authority are not certified.
- Security Master/listing evidence is partial identity evidence only; listing
  presence does not prove that no corporate action occurred for a
  ticker/session/family.
- OJK statistics are an aggregate cross-check only, not ticker-by-session
  exhaustive negative, PIT knowledge-state, or row-level transition authority.

The existing gate therefore remains
`FAIL_STRUCTURAL_CA_COVERAGE_NOT_CERTIFIED`. Its fail-closed requirements still
include structural event completion, date-level population attestation, exact
identity containment, family coverage with source/hash provenance, and temporal
as-of attestation.

## Required future evidence

Before any historical admission, obtain one authoritative source contract that
proves population-wide complete intervals, explicit exhaustive no-event
semantics, stable PIT identity/listing intervals, knowledge/as-of and
observed-through boundaries, revisions/corrections, and source-bound hashes.
Bind that contract to the existing gate and immutable V16 transition census.
Do not infer a narrower population from ticker presence, page absence, current
Security Master state, or resolved transition rows.

## Safety and change boundary

No provider market call, outcome/target access, Phase-E, fit/refit/score,
counter/PaperState/R2 mutation, production execution, deployment, backfill,
Actions rerun, adapter, runtime change, frozen-science change, or admission
state mutation occurred. This checkpoint records evidence only.

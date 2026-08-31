# INC-001 Authority Contract Gap Map V1 Handoff

Date: 2026-08-31 Asia/Jakarta
Lane: `data/ca-aware-feature-basis-remediation-v1`
Audit tree: `b359f1ee381cc0eca98d3b7012a0bb1164658d7a`

## Decision

`AUTHORITY_CONTRACT_GAP_MAP=COMPLETE`

`ADMISSION_READINESS=BLOCKED`

The existing R3 gate already owns the needed boundaries for identity scope,
family coverage, temporal/as-of attestation, source provenance, and semantic
transition certification. Current producer outputs remain observed geometry,
partial positive facts, or fail-closed diagnostics. The missing requirement is
one authoritative population-wide source contract, not another implementation
layer.

## Material gaps

- Population-wide identity/session enumeration is not certified for the 716
  application/closure ticker scope.
- Explicit exhaustive no-event authority is unsupported for IDX and unknown
  for KSEI complete intervals.
- PIT listing intervals, source-defined knowledge/as-of, observed-through, and
  revision/snapshot semantics are not certified.
- V16/V17 transition evidence is manifest-bound and useful for selected event
  semantics, but it does not establish population or historical-as-of
  authority.

The natural KSEI-present and KSEI-certified ticker subsets remain
`population_ca_authority=UNKNOWN`; they cannot be promoted by post-hoc
exclusion without changing V4 cross-sectional population and derived features.

## Minimum closure package

Obtain one immutable source contract and deterministic manifest covering every
required identity/session, every frozen structural family, explicit no-event
semantics, PIT identity/listing intervals, knowledge/as-of and observed-through
boundaries, revision/version lineage, transition semantics, and raw/normalized
hash binding. Feed it into the existing canonical R3 gate only after every
required check is independently verified.

Do not add V2/V3 modules, adapters, fallback providers, or parallel admission
paths to compensate for this evidence gap.

## Boundaries preserved

Read-only and outcome-blind. No source/runtime/science code, immutable artifact,
admission state, provider, production state, counter/PaperState/R2, deployment,
backfill, or Actions rerun was changed.

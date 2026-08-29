# INC-001 cloud economic-reconciliation hardening — V1

Date: 2026-08-29
Lane: `data/ca-aware-feature-basis-remediation-v1`
Cloud continuation parent: `f953e213685881840ccf1722807d3cf0e6e2733a`

## Scope

This checkpoint records a cloud-side hardening continuation while the local
external acquisition root is unavailable to the cloud runtime. It does **not**
claim to finalize the local stock-split acquisition artifact, merge its
continuation ledger, or certify row-level counts that cannot be read from the
local `D:` drive.

No provider call, Phase-E, outcome/target access, fit/refit/scoring, counter
mutation, canonical historical rewrite, production execution, or PR merge is
authorized or performed here.

## Why this hardening is required

The accepted transition-capability probe established that KSEI registered-
security labels `Mandatory Conversion` and `Voluntary Conversion` cannot be
used as economic taxonomy by label alone. The source-native label is retained
as evidence, but a separate source-bound adjudication is required before the
economic event can be classified.

The previous V1.1 raw-source reconstruction remains reproducible and is not
rewritten. A new successor module therefore sits **after** raw-source evidence
reconstruction:

`src/idx_trade/ca_economic_event_reconciliation_v1.py`

Its invariants are:

1. KSEI registered-security `Mandatory Conversion` / `Voluntary Conversion`
   default to `UNRESOLVED_OPERATIONAL_LABEL`, not economic conversion.
2. Source rows collapse only through `PROVEN_SAME_ECONOMIC_EVENT` linkage with
   source reference and valid SHA-256.
3. Source evidence rows are preserved even when multiple representations map
   to one economic event.
4. Tender/cash processes proven `NON_BASIS` become
   `NOT_APPLICABLE_NON_BASIS`, not unresolved price-basis transitions.
5. A resolved transition requires an accepted regular-market semantic, valid
   transition date, source reference, and SHA-256.
6. Conflicting proven economic classifications or transition dates fail
   closed.
7. Collapse arithmetic is asserted:
   `source_rows - cross_source_collapses - same_source_collapses = economic_events`.
8. Transition-state arithmetic is asserted:
   `resolved + unresolved + non_basis = economic_events`.

## Working-count arithmetic review

The local handoff reported the following working reconciliation state:

```text
source evidence rows            = 412
cross-source collapses          = 20
same-source collapses           = 3
reported economic events        = 389
reported resolved transitions   = 153
reported unresolved transitions = 190
reported non-basis excluded     = 46
```

Cloud-side arithmetic is internally coherent:

```text
412 - 20 - 3 = 389
153 + 190 + 46 = 389
```

It also reconciles exactly against the prior transition baseline if the local
row-level evidence truly supports 32 resolution promotions, 46 non-basis
exclusions, and 23 representation collapses:

```text
291 - 32 - 46 - 23 = 190
```

This is an **arithmetic consistency check only**. It is not row-level source
certification because the controlling local root
`D:\Documents\Project\idx-ca-stock-split-acquisition-20260829-v1` is not
available in the cloud runtime.

## Cloud limitation / stop condition

The following local-only inputs were not present in the repository, File
Library, or connected Google Drive during this continuation:

- `provider/index_continuation_2024.json`
- `provider/index_request_ledger.json`
- the ALDO stock-split PDF bound to reported SHA prefix `99867e65...`
- the ISAT stock-split PDF bound to reported SHA prefix `7a8a3166...`
- the unfinished local stock-split acquisition root itself

Therefore this checkpoint deliberately does not fabricate:

- a merged request ledger;
- a new immutable economic-reconciliation manifest;
- exact row-level collapse/adjudication records;
- deterministic artifact comparison over unavailable bytes.

Those steps remain blocked on access to the already-acquired local evidence,
not on additional provider acquisition.

## Scientific state

The latest reported local working state remains planning evidence only until
row-level artifact reconciliation is run against the actual retained bytes:

```text
REPORTED_SOURCE_ROWS             = 412
REPORTED_ECONOMIC_EVENTS         = 389
REPORTED_RESOLVED_TRANSITIONS    = 153
REPORTED_UNRESOLVED_TRANSITIONS  = 190
REPORTED_NON_BASIS_EXCLUDED      = 46

DATA_ADMISSION       = FAIL
RESEARCH_ADMISSION   = FAIL
PHASE_E_AUTHORIZED   = FALSE
REFIT_AUTHORIZED     = FALSE
COUNTER_ACTION       = NONE
```

The code hardening in this checkpoint is safe to validate independently in CI
because it is pure/local-only and does not require provider data.

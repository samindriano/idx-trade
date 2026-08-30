# INC-001 closure feasibility checkpoint V1

Date: 2026-08-31  
Lane: `data/ca-aware-feature-basis-remediation-v1`  
Controlling reconciliation: `D:\Documents\Project\idx-ca-economic-event-reconciliation-20260831-v16-composite-policy`  
Manifest SHA-256: `3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030`

## Final known-event census

The current reconciliation contains 412 source rows, 387 economic events, 163
resolved transitions, 178 unresolved transitions, 46 non-basis events, and 27
proven linkages. The four composite cash+share events are
`COMPOSITE_CASH_SHARE_DISTRIBUTION`, basis-changing, and unresolved. MERGER=5
and CAPITAL_RESTRUCTURING=19 remain unresolved. No unresolved taxonomy remains
in V16.

Known-event remediation is materially complete for the authorized work:
remaining event families are parked fail-closed. The bounded MERGER artifact
manifest is `747c83ac3bcf6dac15e73c1e71553a0ae80422b9da0f25deb57b3139dceff6c1`;
the CAPITAL artifact manifest is
`a4f4fd188d830088cdafbb1bbcd5716ae1f92cc6fcd8314181cf9dbefa832887`.

## Closure feasibility

The existing outcome-blind R3.1 geometry artifact was used as geometry evidence,
not recomputed and not treated as the current 387-event census:

- fit: 240,344 rows / 629 tickers;
- application: 276,153 rows / 716 tickers;
- observed dependency closure: 365,968 rows / 716 tickers;
- existing global gate: `FAIL_STRUCTURAL_CA_COVERAGE_NOT_CERTIFIED`.

No row-level split into `BASIS_SAFE`, `BASIS_UNSAFE`, known-event `BASIS_UNKNOWN`,
and population-authority `BASIS_UNKNOWN` is certified by the current evidence.
The exact split was deliberately not estimated. Certified safe rows in this
closure decision: 0.

Artifact: `D:\Documents\Project\idx-ca-inc001-closure-feasibility-20260831-v1`  
Manifest SHA-256: `42a1e20f29ef4028ecfaae99f032dd138511c6fd1bf5242c66c057683cc4172c`

Verdicts:

- `KNOWN_EVENT_REMEDIATION=MATERIAL_WORK_COMPLETE`;
- `KNOWN_EVENT_LONG_TAIL=PARKED_FAIL_CLOSED`;
- `POPULATION_COMPLETENESS=UNKNOWN`;
- `HISTORICAL_ASOF_AUTHORITY=UNKNOWN`;
- `INC001_INCIDENT_CLOSURE=BLOCKED_ON_POPULATION_AUTHORITY`.

The remaining blocker is an authoritative population-wide no-event/completeness
and historical as-of contract. Do not continue event-by-event archaeology or
infer safe rows from event absence.

Guardrails: read-only and outcome-blind; no feature recomputation for model
use, outcomes, refit, scoring, counter/PaperState, production, backfill,
deployment, or merge.

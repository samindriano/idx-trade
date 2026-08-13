# Path Risk V2 — Schema Guard Pre-Outcome Block

Date: 2026-08-11 (Asia/Jakarta)
Status: **PRE-OUTCOME BLOCK REVIEWED / IMPLEMENTATION CORRECTED / PR-002+PR-003 STILL UNVIEWED**

## What happened

The first authorized Path Risk V2 discovery invocation stopped before row/outcome
values were read and before any model fit/score/metric because the physical
Parquet schema guard introduced during parallel hardening described the frozen
V1 joined model table incorrectly.

Blocked source HEAD:

`3472baf41c10abe4e05e0eeef058e27231e7bc00`

The guard expected a projected V2 read view beginning with identity + target
metadata, followed by the 33 features. The immutable frozen V1 artifact actually
preserves the V1 join output schema:

```text
ticker
date
signal_session_index
universe_primary_liquid
<exact frozen 33 features>
label_status
first_barrier_date
target_tau_date
adverse_excursion_r
```

That physical layout is consistent with the frozen V1 discovery implementation:
the primary-liquid feature cache is the merge-left table and target metadata is
appended by the one-to-one target join.

The immutable artifact SHA remained exactly:

`b66fc7e40f18940ae9db418331a421e0f36d23b86597500b1d3ba73a8e3777fe`.

## Outcome state

The failed invocation created an empty `_001` output directory only.

- row/outcome values read: `false`;
- PR-002 fit/score/metrics: `false`;
- PR-003 fit/score/metrics: `false`;
- candidate ordinal consumed: `false`;
- F5/F6 accessed: `false`;
- fresh-forward accessed: `false`;
- `FORWARD_OUTCOME_ACCESS_STARTED` written: `false`.

Therefore a corrected pre-outcome retry is allowed without treating either V2
candidate as viewed.

## Correction

The runner now separates:

1. the exact physical frozen V1 artifact schema; and
2. the narrower column projection actually needed by V2 modelling.

Physical schema validation remains fail-closed: missing, additional, or
reordered physical columns are rejected. The expected schema itself is now the
schema of the SHA-pinned frozen V1 artifact, including
`universe_primary_liquid` and `target_tau_date`.

No Path Risk V2 scientific semantics changed:

- PR-002/PR-003 definitions unchanged;
- exact 33 feature order unchanged;
- target unchanged;
- folds unchanged;
- hyperparameters unchanged;
- metrics/gates/selection unchanged;
- F5/F6 seal unchanged;
- final V3-B ranker unchanged.

Regression coverage was updated to encode the correct physical artifact schema
and continue rejecting missing/extra/reordered schemas.

## Retry boundary

The abandoned `_001` directory must not be reused. The next authorized
execution uses:

`path_risk_v2_discovery_run_20260811_002`

and follows:

`coordination/handoffs/IDX-PATH-RISK-V2-DISCOVERY-F1-F4-RUN.md`.

A full local pytest pass is required again before the real runner starts.

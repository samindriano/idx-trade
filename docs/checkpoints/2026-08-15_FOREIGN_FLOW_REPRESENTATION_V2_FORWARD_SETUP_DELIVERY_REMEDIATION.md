# Foreign Flow Representation V2 — Prospective Setup State Delivery Remediation

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/foreign-flow-representation-v2-forward-v1`

Review basis: `review/idx-foreign-flow-representation-v2-forward-v1-r2@1ff97280067a65cc61f15c5f4adc5fa33ccb4c9e`

Status: `REVIEW`

## Decision

`FOREIGN_FLOW_V2_FORWARD_SETUP_DELIVERY_REMEDIATED_REVIEW_REQUIRED`

Representation V2 and Setup State V1 are now aligned to the frozen causal
timing contract. A completed source session `t` produces an immutable
Representation V2 pair for the next official feature session `t+1`, and the
producer immediately materializes and verifies the deterministic Setup State
sidecar from that pair.

The Setup State path does not require a `t+1` session directory, market rows,
Foreign Flow rows, or EOD completion. It reads only the verified prospective
Representation V2 parquet/manifest and its hash-pinned official calendar.

No real runtime run was attempted. The current rolling context after
2026-07-31 remains incomplete and therefore remains outside this remediation.

## Implementation

Added prospective-only functions in
`src/idx_trade/forward_foreign_flow_setup.py`:

- `enrich_prospective_foreign_flow_setup(...)`
- `verify_prospective_foreign_flow_setup(...)`

The functions:

1. require the exact forward Representation V2 status, artifact SHA, and
   outcome-blind manifest flags;
2. require source/feature sessions from the Representation V2 manifest and
   verify that `feature_session=t+1` is the next official date after
   `flow_through_session=t`;
3. verify the official calendar path and SHA from Representation V2 input
   provenance;
4. reuse `build_foreign_flow_setup_sidecar(...)` and the unchanged
   `DEFAULT_THRESHOLDS` classifier contract;
5. write `idx_foreign_flow_setup.parquet` and a separate immutable
   `idx_foreign_flow_setup.manifest.json` beside the prospective V2 pair;
6. record source-session, calendar, Representation V2 hashes, thresholds,
   `target_session_captured=false`, `provider_calls=0`, and outcome-blind
   flags; and
7. fail closed on missing/ambiguous provenance, calendar mismatch, SHA or
   sidecar revision conflicts, duplicate keys, non-causal dates, or prohibited
   representation content.

`produce_session_foreign_flow_representation_v2(...)` now calls the
prospective Setup State materializer immediately after the Representation V2
pair is created. Existing `run_foreign_flow_catchup()` remains unchanged for
later canonical-session consumption and no second scheduler, capture system,
counter, or runtime hierarchy was introduced.

## Tests

Added regression coverage proving:

- Setup State is available in the prospective folder before any target session
  directory exists;
- later target-session market/Foreign Flow files do not change the immutable
  prospective sidecar or manifest;
- a Representation V2 byte revision after Setup State creation is rejected by
  both verification and materialization.
- malformed access flags/counts, calendar revision, and an output directory
  outside the prospective V2 folder are rejected.

Focused command:

```text
python -m pytest tests/test_forward_foreign_flow_setup.py tests/test_forward_foreign_flow_representation_v2.py tests/test_foreign_flow_features_v2.py tests/test_foreign_flow_representation_v2_runner.py -q
```

Result: `32 passed, 5 warnings`.

Full command:

```text
python -m pytest -q
```

Result: `117 collected; 116 passed, 1 failed, 5 warnings`.

The sole failure remains the unrelated pre-existing
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`:
the current storage audit emits two independent conflicts (`raw_close` and
`vendor_adj_close`) while that old test expects one. No storage file was
changed.

`git diff --check`: PASS.

## Boundaries

No provider calls, real capture, historical backfill, model fit/scoring,
outcome/label access, O2 change, scheduler/counter change, free-float/HSC
integration, or price-state work occurred. The implementation is ready for
independent review, but current local rolling context is still
`NO_GO_CURRENT_CONTEXT` until the existing calendar/market/Foreign Flow owner
provides a complete post-2026-07-31 extension.

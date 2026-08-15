# Foreign Flow Setup State V1 Runtime Wiring

Date: 2026-08-15
Branch: `research/idx-foreign-flow-setup-state-v1`
Implementation commit: `7db73a5`
Status: `REVIEW`

## Scope

This change wires the descriptive Foreign Flow Setup State V1 sidecar into the
accepted Foreign Flow prospective sidecar catch-up boundary. It does not add a
capture engine, scheduler, counter, provider call, model, score, label, or
outcome path.

The existing raw flow path remains authoritative:

1. validate the canonical DATA_READY session and immutable Stock Summary raw
   response;
2. create or verify `idx_foreign_flow.parquet` and its manifest;
3. if the same session has a separately materialized,
   outcome-blind Representation V2 artifact, validate it and create or verify
   the Setup State sidecar.

The runtime never reconstructs Representation V2 from one raw session. This is
intentional: own-history percentile, rolling state, and cross-sectional ranks
cannot be safely invented from a single session.

## Representation input contract

For a session directory, the optional V2 input pair is:

- `foreign_flow_representation_v2.parquet`
- `foreign_flow_representation_v2.manifest.json`

The adapter requires the exact accepted V2 output schema, rejects extra columns
(including outcome-like/future columns), pins the parquet SHA in the V2
manifest, requires outcome-blind provenance, and verifies the parent official
calendar SHA. Every row must have a non-null identity, the target
`feature_session`, and `flow_through_session` equal to the immediately prior
official session.

## Setup artifacts

For an accepted representation input, the runtime creates immutably:

- `idx_foreign_flow_setup.parquet`
- `idx_foreign_flow_setup.manifest.json`

The sidecar preserves participation, shock 1/5/20, own-history percentile,
all three shock cross-sectional ranks, persistence, acceleration, and 5/20
divergence evidence, plus deterministic state axes, setup label, explicit
missingness, source version, parent manifest/raw SHA, Representation V2
artifact/manifest SHA, and observed retrieval availability.

The label `STEALTH_ACCUMULATION_CANDIDATE` remains descriptive WATCH/setup state
only. It is not a BUY signal and is not registered in a counter.

## Fail-closed and idempotency hardening

- null/empty/duplicate identity keys fail closed;
- non-causal or non-official session alignment fails closed;
- missing or invalid V2 source hashes fail closed;
- unexpected representation columns fail closed;
- missing preserved evidence makes the state axes/label `INDETERMINATE` and
  records the missing fields;
- invalid persistence/divergence domains produce an indeterminate state;
- an existing sidecar or manifest is never overwritten; a revision conflict
  fails closed;
- no provider, outcome, label, model, O2, free-float, or effective-supply
  access is present.

Sessions with valid raw Foreign Flow but no Representation V2 pair are reported
as `setup_state_skipped_no_representation`. They remain raw-flow ready and do
not silently receive a setup state.

## Validation

Focused command:

```text
python -m pytest tests/test_foreign_flow_setup_state.py tests/test_foreign_flow_setup_sidecar.py tests/test_forward_foreign_flow.py tests/test_forward_foreign_flow_sidecar.py tests/test_forward_foreign_flow_setup.py -q
```

Result: `38 passed`.

Full command:

```text
python -m pytest -q
```

Result: `105 passed, 1 failed, 0 warnings` out of `106` collected. The only
failure is the pre-existing unrelated
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`:
the test expects one conflict while current storage returns two independent
audit conflicts (`raw_close` and `vendor_adj_close`). No storage file was
changed in this lane.

`git diff --check`: passed.

## Readiness decision

The Setup State adapter and catch-up integration are **conditionally runtime
ready**: a future V2 representation producer can place the exact verified input
pair in the canonical session directory and the existing catch-up runtime will
materialize the setup sidecar without a second capture path. The currently
recorded 2026-08-11/12 sessions contain raw Foreign Flow but no V2
representation pair, so they are correctly skipped rather than backfilled.

No historical performance evaluation or price-confirmation layer was started.

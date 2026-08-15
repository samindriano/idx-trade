# Foreign Flow Representation V2 Prospective Producer

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/foreign-flow-representation-v2-forward-v1`

## Decision

`FOREIGN_FLOW_V2_FORWARD_PRODUCER_IMPLEMENTED_REVIEW_REQUIRED`

The producer is outcome-blind and reuses the accepted
`idx_trade.foreign_flow_features_v2.build_foreign_flow_representation_v2`
implementation. It materializes one target feature session only after the
canonical EOD session is `DATA_READY`, its Foreign Flow sidecar and market
artifacts verify, and a complete official calendar/context extension is
available.

No real forward session was materialized in this task. In particular, the
existing 2026-08-11/12 artifacts were not retroactively enriched or
synthetically backfilled.

## Implementation

New module: `src/idx_trade/forward_foreign_flow_representation_v2.py`.

The public entrypoint is:

`produce_session_foreign_flow_representation_v2(...)`

It accepts explicit paths and SHA-256 pins for the accepted historical Foreign
Flow archive, historical market panel, official session calendar, and PIT
security master. It then:

1. verifies the pinned historical inputs;
2. reads only verified canonical forward `DATA_READY` sessions through the
   requested target;
3. combines historical context with those immutable forward session rows in
   memory, rejecting duplicate/conflicting ticker-session identities;
4. rejects any missing official extension session instead of silently
   compressing the calendar or forward-filling state;
5. calls the frozen V2 builder without changing formulas, windows, ranks, or
   listing semantics;
6. filters to exactly `feature_session=t+1` and asserts
   `flow_through_session=t`;
7. writes the representation parquet and manifest with exclusive creation;
8. invokes the existing `run_foreign_flow_catchup()` so Setup State V1 remains
   the only downstream sidecar path.

Rolling context is preserved by deterministic replay from the pinned archive
   plus verified forward session artifacts, rather than a mutable unverified
   accumulator. The builder therefore retains the full history needed for the
   20-session turnover baseline, 5/20-session windows, 120-session own-history
   percentile, persistence/acceleration, and same-source-session
   primary-liquid ranks/divergence.

The producer requires the supplied official calendar to be the same path and
SHA declared by the target session manifest. This prevents a sparse or stale
runtime calendar from treating a missing official session as the next session.
The current local runtime calendar contains only 2026-08-10 through
2026-08-12, so a real live run remains correctly blocked until the existing
calendar-sync/capture path supplies the complete official extension.

Read-only runtime audit found the same boundary independently: 2026-08-10 is
incomplete (`rows=962` against `recordsTotal=963`) and has no canonical raw
JSON/Foreign Flow sidecar; 2026-08-11 and 2026-08-12 have verified raw
Foreign Flow sidecars but no V2 representation pair. The pinned historical
market panel ends at 2026-07-31, while the separately observed extension
calendar for 2026-08-03 through 2026-08-11 is itself marked blocked. Therefore
the producer must not compress 2026-08-03 through 2026-08-07 out of the
calendar or use 2026-08-11/12 as synthetic repairs. The first genuinely new
target remains blocked until a versioned, complete official calendar and
market/flow context extension are supplied by the existing capture/calendar
owner.

## Artifact contract

For a target session, the output is written in that canonical session folder:

- `foreign_flow_representation_v2.parquet`
- `foreign_flow_representation_v2.manifest.json`

The parquet uses the exact accepted V2 columns:
`ticker`, `feature_session`, `flow_through_session`, and the 15 frozen V2
features. The manifest pins the artifact SHA, builder identity, source and
calendar hashes, target/source sessions, rolling-context policy, row/ticker
counts, feature availability, and causal diagnostics. It records:
`outcome_blind=true`, `fresh_forward_accessed=false`,
`outcomes_or_labels_accessed=false`, `provider_calls=0`, and no publication
time claim from observed retrieval timestamps.

Existing artifacts are never overwritten. A rerun recomputes and verifies the
same immutable artifact/manifest pair; changed bytes, source identity, or
manifest metadata fail closed as a revision conflict.

## Validation

Focused Foreign Flow V2/producer/setup/runner tests:

`24 passed`

Full repository suite from the repository root:

`294 passed, 1 failed, 3 warnings`

The one failure is the pre-existing unrelated
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`:
the current storage contract emits two independent conflicts
(`raw_close` and `vendor_adj_close`) while that old test expects one. No
storage file was changed in this lane.

`git diff --check`: PASS.

The focused producer tests cover causal invariance of all 15 features when
the target session changes, exact `t` to `t+1` mapping, hash-pinned manifest
creation, idempotent no-overwrite rerun, and fail-closed missing target/prior
evidence.

## Boundaries

No provider calls, historical performance test, model fit/scoring, outcome or
label access, synthetic 2026-08-11/12 backfill, free-float/HSC integration,
price-state layer, or O2 modification occurred.

Next action is independent review of the producer contract and the existing
calendar-sync integration before using it for a genuinely new live EOD
session. The runtime readiness verdict is currently `NO_GO_CURRENT_CONTEXT`
for the local artifacts, not a rejection of the frozen V2 feature formulas.

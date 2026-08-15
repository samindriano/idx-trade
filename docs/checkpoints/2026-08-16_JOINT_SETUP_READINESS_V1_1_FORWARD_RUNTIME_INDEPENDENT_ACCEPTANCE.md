# Joint Setup Readiness V1.1 Forward Runtime — Independent Acceptance

Date: 2026-08-16

Reviewed implementation:
`integration/joint-setup-readiness-v1-1-forward-v1@8ede786622713b03127fbf856abe2d7d2bd5c03d`

Accepted scientific parent:
`research/idx-joint-setup-readiness-state-v1-1-domain-remediation@af2450c7e5166dba853a810ee77ebdc339198dc7`

Frozen V1.1 fingerprint:
`c1bd084dfe54dacd447ee15915e5210e539cfc99b19f42f1543bfa3f1801d5de`

## Verdict

`JOINT_SETUP_READINESS_V1_1_CONTROLLED_RUNTIME_ACCEPTED_GENERIC_DAILY_RUNNER_NEXT`

The controlled prospective runtime result is accepted for the exact frozen
2026-08-12 -> 2026-08-13 parent pair.

Accepted runtime identities:

- rows/tickers: `836 / 836`
- Foreign Flow keys: `963`
- Price State authoritative keys: `836`
- overlap: `836`
- Price-only: `0`
- Foreign-Flow-only excluded: `127`
- state distribution: `IGNORE=697`, `WATCH=84`, `READY=54`, `ENTRY_ELIGIBLE=1`
- joint artifact SHA-256: `d83593b61a25f9f32a82c153001e0c548f29ffb255485b29a84760ae6ae03418`
- joint manifest SHA-256: `c3007af5af3061ee91be176fb0d29dc000cfc162fcc0c3642c5f26723646d646`

## Review findings

1. The runtime adapter pins and re-hashes the exact accepted Foreign Flow Setup
   and Price State artifact/manifest bytes before building the joint output.
2. Parent row contract versions, status, explicit protected flags, duplicate
   identities, source session, feature session, and row counts are checked
   fail-closed.
3. The accepted V1.1 builder recomputes the Price-domain subset relation before
   materialization; required Price keys cannot be silently dropped by an inner
   join.
4. The strict verifier rebuilds the joint state from reopened parent bytes and
   compares the entire output frame exactly, including states and schema.
5. Domain provenance includes the exact 127 Foreign-Flow-only identities.
6. The smoke distribution is recomputed from parent data and then compared to
   the frozen preflight expectation; it is not injected into the classifier.
7. The immutable pair was created once; the permitted replay returned
   `created=false` with identical artifact and manifest hashes.
8. The runtime remains outcome-blind and descriptive-only: provider calls zero,
   no outcomes/labels, no model fit/scoring, and no trade recommendation.

Focused tests recorded: `33 passed`.
Full suite recorded: `72 passed, 1 known unrelated storage expectation failure,
73 collected`. The storage failure is outside this lane.

## Boundary / next action

Acceptance is for the exact controlled-smoke adapter and immutable 2026-08-13
artifact only. The checked-in runner is intentionally frozen to
`SOURCE_SESSION=2026-08-12`, `FEATURE_SESSION=2026-08-13`, exact parent hashes,
and the smoke-domain/state expectations.

Therefore it is **not yet a generic daily scheduler runner**. Do not hook this
module directly into routine scheduling.

Next authorized lane is a narrowly scoped generic prospective runner that:

- accepts a requested source/feature session rather than hard-coded dates;
- discovers and strictly verifies the already-materialized Foreign Flow Setup
  and Price State parents for that feature session;
- preserves V1.1 fingerprint and Price-domain subset semantics unchanged;
- does not freeze future domain counts or state distributions;
- writes the same immutable/idempotent joint artifact contract;
- fails closed if either parent is missing/not verified;
- performs no provider calls, outcome access, model/scoring, O2/counter changes,
  or threshold/mapping changes;
- remains separate from scheduler integration until its own controlled replay
  and independent review pass.

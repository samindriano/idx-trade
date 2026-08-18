# V4-3 CA training-domain — residual attribution prep

Date: 2026-08-19 Asia/Jakarta
Branch: `data/v4-3-ca-training-domain-ksei-129-v1`
Status: `READY_FOR_OFFLINE_RESIDUAL_ATTRIBUTION`

## Immutable parent result

The KSEI-129 offline overlay replay remains blocked and is pinned by manifest
SHA-256:

`c115ea0bec59cab4da0cda45ee66ba2be5814e0bb9e854e3f7ecd616edc83861`.

Observed outcome-blind state:

- CA census identities: 740;
- certified coverage: 695;
- unresolved decision-domain coverage: 45;
- missing decision-domain identities: 0;
- KSEI-129 delta: 93 certified / 36 unresolved;
- frozen validation minimum combined support: H5 0.8050847457627118,
  H10/consensus 0.7942386831275721;
- eligible sessions: 0 H5 / 0 H10 / 0 consensus;
- no historical target, rank, model, prediction, performance, provider, network,
  or protected-forward outcome access occurred during the offline replay.

The unchanged minimum rate after the 93/129 overlay is not interpreted by
inspection alone. A formal attribution is required before deciding whether to
retry coverage, acquire exact schedules, or stop for a structural blocker.

## Frozen attribution

Config:
`config/v4_3_ca_training_domain_residual_attribution_v1.json`

Runner:
`scripts/run_v4_3_ca_training_domain_residual_attribution.py`

The audit consumes only the immutable offline replay artifacts and computes:

1. `BASELINE` — exact parent replay;
2. `COVERAGE_ONLY_CEILING` — hypothetically certifies **all** unresolved
   coverage rows, with schedule-required events and exact crossings still
   blocked;
3. `SCHEDULE_ONLY_CEILING` — hypothetically resolves **all** schedule-required
   rows, with unresolved coverage and exact crossings still blocked;
4. `COVERAGE_PLUS_SCHEDULE_CEILING` — hypothetically resolves both remediable
   evidence classes while exact mechanical crossings remain blocked;
5. `PRICE_OBSERVABILITY_ONLY_UPPER_BOUND` — diagnostic-only upper bound that
   ignores CA entirely and can never authorize target access.

The runner additionally emits complete unresolved-coverage ticker impact and
schedule-event impact ledgers. These are diagnostics only: no minimal/pass-
preserving subset is selected. If coverage remediation is indicated, the
boundary remains all unresolved coverage tickers, not only the smallest subset
needed to exceed 90%.

## Scientific guardrails

- frozen gate stays exactly `>=0.90`;
- frozen 600 validation identity is hash-pinned;
- exact mechanical crossing rows are never waived by an admissible ceiling;
- no provider/network/retry in this lane;
- no source substitution or parser/semantic relaxation;
- no target/rank materialization;
- no model fit/prediction/performance;
- no protected-forward access;
- no scientific parameter change.

## Decision interpretation

- `...COVERAGE_ONLY_SUFFICIENT`: recover all 45 unresolved coverage identities,
  then replay unchanged semantics.
- `...SCHEDULE_ONLY_SUFFICIENT`: acquire exact official schedules for all
  schedule-required events, then replay.
- `...COVERAGE_PLUS_SCHEDULE_REQUIRED`: both evidence classes need remediation.
- `...EXACT_CROSSING_OR_INTERSECTION_STRUCTURAL_BLOCKER`: even all remediable
  CA evidence cannot preserve the frozen 600 while exact crossings remain
  correctly blocked; do not waive crossings.
- `...PRICE_OBSERVABILITY_STRUCTURAL_BLOCKER`: even ignoring CA cannot recover
  the frozen gate; stop for frozen target-support review.

The counterfactual ceilings are attribution devices only and are not historical
execution authorization.

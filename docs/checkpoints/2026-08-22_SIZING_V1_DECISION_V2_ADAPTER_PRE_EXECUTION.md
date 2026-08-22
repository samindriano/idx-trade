# Sizing V1 — Decision V2 Adapter Before Execution Audit

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`

## Scope

Adapt the already frozen/hard-audited Sizing V1 allocator to the frozen incumbent Decision V2 Minimal policy without changing the economic sizing policy or lot-allocation objective.

## Implemented

- Created the canonical E2E branch from accepted `research/idx-decision-v2-minimal-implementation-v1`.
- Preserved one Sizing V1 allocation implementation by extracting a decision-rule-neutral internal `_size_entries_core`.
- Retained the legacy Decision V1 public path and private `_size_entries_for_intents` entry point so existing Execution V1 remains source-compatible until its own adapter remediation.
- Added `v4_x1_sizing_v1_decision_v2_adapter.py`.
- Decision V2 provenance is verified by exact recomputation with `plan_v4_x1_decision_v2_minimal`; a V2 plan is never projected or mislabeled as `V4_X1_DECISION_V1`.
- Sizing config now explicitly admits only:
  - `V4_X1_DECISION_V1` for legacy compatibility;
  - `V4_X1_DECISION_V2_MINIMAL_V1` for the frozen incumbent.
- Frozen sizing economics remain unchanged:
  - 100-share lots;
  - ~10% NAV target per new entry;
  - 15% new-entry cap;
  - no conviction/rank weighting;
  - rank used only as deterministic exact-objective tie-break;
  - no HOLD rebalance;
  - no strategic exposure overlay;
  - residual cash allowed;
  - Close(t) sizing reference; fees/Open gaps/capacity remain Execution-layer mechanics.

## Regression locks added

- forged Decision V2 plan fails provenance verification;
- raw/unverified Decision V2 plan cannot call sizing;
- Decision V2 bootstrap at Rp50m / ten equal Rp1,000 names sizes 50 lots/name;
- V2 adapter output must be exactly equal to legacy V1 Sizing output for an equivalent BUY set and price map;
- Decision V2 temporary underfill does not renormalize remaining entrants above 10% merely because cash is available;
- legacy Sizing V1 config/provenance tests remain retained.

## Remaining Sizing items

### Required before calling Sizing V1 fully E2E-ready

1. **Fresh local test run** on this exact branch: focused Sizing V1 + Decision V2 adapter tests, plus the existing Execution V1 allocator regressions because Execution imports the retained legacy `_size_entries_for_intents` entry point.
2. **Static compile/import smoke** for the modified Sizing module and new adapter.

These are validation tasks, not known code defects.

### Non-blocking technical debt

- Generic Sizing validation errors still use the historical `DecisionV1Error` namespace. This is naming/exception-taxonomy debt only; changing it before E2E would create unnecessary churn.
- `SizingPlan` itself does not persist the full Decision V2 provenance bundle. The verified V2 plan identity must therefore be carried into the Execution/E2E order-plan lineage rather than inferred from `SizingPlan` alone.

## Execution boundary discovered

Execution V1 is still explicitly bound to legacy Decision V1 types (`DecisionPlan`, `TradeIntent`, `VerifiedDecisionPlan`) and imports `_size_entries_for_intents`. This is the next remediation target. Do not modify Sizing economics to work around it; adapt Execution provenance/intents to frozen Decision V2 while preserving its already-remediated fee, Open-gap, capacity, pending-transition, and CA behavior.

## Verdict

`SIZING_V1_DECISION_V2_ADAPTER_IMPLEMENTED_MATH_UNCHANGED_PENDING_FRESH_LOCAL_VALIDATION_EXECUTION_ADAPTER_NEXT`

# Sizing V1 — Decision V2 Adapter Accepted Before Execution Audit

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`
Validated implementation HEAD: `3ab20c6de58dd4fa4b57c7adf48c71ea302cc3cd`

## Scope

Adapt the already frozen/hard-audited Sizing V1 allocator to the frozen incumbent Decision V2 Minimal policy without changing the economic sizing policy or lot-allocation objective.

## Implemented

- Created the canonical E2E branch from accepted `research/idx-decision-v2-minimal-implementation-v1`.
- Preserved one Sizing V1 allocation implementation by extracting a decision-rule-neutral internal `_size_entries_core`.
- Retained the legacy Decision V1 public path and private `_size_entries_for_intents` entry point so existing Execution V1 remains source-compatible until its own adapter remediation.
- Added `v4_x1_sizing_v1_decision_v2_adapter.py`.
- Decision V2 provenance is verified by exact recomputation with `plan_v4_x1_decision_v2_minimal`; a V2 plan is never projected or mislabeled as `V4_X1_DECISION_V1`.
- Sizing config explicitly admits only:
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

## Regression locks

- forged Decision V2 plan fails provenance verification;
- raw/unverified Decision V2 plan cannot call sizing;
- Decision V2 bootstrap at Rp50m / ten equal Rp1,000 names sizes 50 lots/name;
- V2 adapter output must be exactly equal to legacy V1 Sizing output for an equivalent BUY set and price map;
- Decision V2 temporary underfill does not renormalize remaining entrants above 10% merely because cash is available;
- legacy Sizing V1 config/provenance tests remain retained.

## Fresh local validation

Validated by Codex on exact HEAD `3ab20c6de58dd4fa4b57c7adf48c71ea302cc3cd`:

- working tree: clean;
- static compile/import: PASS;
- `git diff --check`: PASS;
- focused tests: **40 passed, 0 failed, 0 skipped**;
- Decision V1 legacy sizing: PASS;
- Decision V2 provenance adapter: PASS;
- forged/unverified V2 rejection: PASS;
- V1/V2 allocation equivalence: PASS;
- underfill no-renormalization: PASS;
- Execution legacy `_size_entries_for_intents` import compatibility: PASS;
- config hash verification: PASS;
- no provider call or protected outcome access.

## Remaining Sizing items

There are **no known Sizing V1 algorithm defects blocking E2E**.

Non-blocking technical debt only:

- generic Sizing validation errors still use the historical `DecisionV1Error` namespace; this is naming/exception-taxonomy debt and is intentionally not churned before E2E;
- `SizingPlan` does not persist the full Decision V2 provenance bundle. The verified V2 plan identity must be carried into the Execution/E2E order-plan lineage rather than inferred from `SizingPlan` alone.

## Execution boundary

Execution V1 is still explicitly bound to legacy Decision V1 types (`DecisionPlan`, `TradeIntent`, `VerifiedDecisionPlan`) and imports `_size_entries_for_intents`. This is the next remediation target. Do not modify Sizing economics to work around it; adapt Execution provenance/intents to frozen Decision V2 while preserving its already-remediated fee, Open-gap, capacity, pending-transition, and CA behavior.

## Verdict

`SIZING_V1_DECISION_V2_ADAPTER_ACCEPTED_E2E_READY_EXECUTION_AUDIT_NEXT`

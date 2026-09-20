# IDX Exposure/Cash State Taxonomy Audit V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Runtime under audit: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational`
Runtime branch: `runtime/idx-e2e-baseline-paper-v1`
Runtime HEAD: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Verdict

`FAIL — EXPOSURE_CASH_CAUSE_IS_NOT_BOUND_TO_RESTARTABLE_STATE`

The Decision artifact records `capacity_state` and `unfilled_slots`, but the
restartable paper state does not. Execution cause/status and risk-hold cause
are also not state-owned. The next Decision reconstructs shadow membership from
positions and ticker-level pending rows only. Consequently, different upstream
histories can converge to the same state payload and state hash even though
their operational remediation and economic interpretation differ.

## Exact pinned evidence

The read-only probe `research/idx_exposure_cash_state_taxonomy_probe_v1.py`
used AST/source inspection against runtime HEAD `402fca4b...` and did not import,
execute, or write the runtime. It found:

- `DecisionV2Plan` has `unfilled_slots` and `capacity_state`;
- the Decision artifact serializer preserves both fields;
- the declared Decision capacity states are only `FULL` and
  `UNFILLED_NO_QUALIFIED_CHALLENGER`;
- `PaperPortfolioState` has only session date, cash, positions, pending buys,
  pending sells, reconciliation flag, and source;
- the state payload has no `capacity_state`, `unfilled_slots`, cash-cause,
  Open-availability, risk-hold, or fill-status-history field;
- `reconstruct_decision_shadow_state` uses positions, removes pending sells,
  and adds pending buys, without restoring any cause taxonomy;
- two synthetic histories produced the same state payload hash:
  `NO_QUALIFIED_CHALLENGER` and `EXECUTION_CAPACITY_LIMITED`;
- `writes_performed=False`.

The Decision artifact is not itself lost. The boundary defect is that the
cause is not joined to the durable state consumed by restart and the next
Decision. Completed execution artifacts may retain fill statuses separately,
but the state owner has no typed causal link to them.

## Why it matters

The same cash/position state can mean materially different things:

1. intentional residual cash because no qualified challenger existed;
2. unavailable Open or zero reference-day capacity;
3. a pending or underfilled obligation;
4. a future risk hold, if a risk overlay is later introduced.

Those cases should not automatically share the same replan, retry, expiry,
risk, or scientific-interpretation policy. Hash equality proves serialization
integrity, not causal completeness. This finding composes with the existing
positive-partial-buy, pending-lifecycle, CA-settlement, and reconciliation-flag
findings; it does not claim that the current position arithmetic is corrupted.

## Classification and reopen condition

Classification: `CROSS_COMPONENT DEFECT / OBSERVABILITY GAP / ECONOMIC
INTERPRETATION RISK`.

Do not rerun the same static probe as a new defect. Reopen only with an
authorized versioned exposure/cash-state contract that defines the state owner,
cause taxonomy, obligation join, risk-hold semantics, and replay/restart
behavior. The contract must preserve historical artifacts without fabricating
legacy causes.

## Validation and boundaries

- Focused probe test: `1 passed`.
- Probe and test compilation: passed.
- No runtime source, canonical data, provider, cloud/capture/telemetry,
  scheduler, incumbent state, or protected outcome was mutated or opened.
- No model smoke, retry, push, merge, or production action was performed.

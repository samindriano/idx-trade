# IDX Prospective Formula-Independence Audit V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`

## Verdict

`UNKNOWN — PROSPECTIVE_FORMULA_INDEPENDENCE_NOT_ESTABLISHED`

The protected-access gate independently validates many input, provenance,
identity, and code-pin conditions, but it does not independently recompute the
metric formulas. It imports and calls the same frozen metric functions used by
the development evaluator.

This is not evidence that the formulas are wrong. It means current green
consistency tests cannot detect a shared formula error or a shared semantic
misinterpretation.

## Exact evidence

The read-only probe `research/idx_prospective_evaluator_formula_independence_probe_v1.py`
was pinned to these source hashes:

| Source | SHA-256 |
|---|---|
| `src/idx_trade/prospective_evaluation_v1.py` | `98658814531367cf779af71698c2db77ae454900c1f86b84dddf1db0ca834108` |
| `src/idx_trade/prospective_evaluation_gate_v1.py` | `41a5ca7987b529675bc1ef1858b50b763467d3d5651f92178e4d74275f09052a` |

For all five metric functions—`evaluate_alpha_metrics`,
`evaluate_portfolio_metrics`, `evaluate_turnover`, `evaluate_pending_orders`,
and `evaluate_benchmark`—the probe found:

- the gate module has the same function object as the evaluator module;
- the gate defines no independent implementation of those functions;
- the gate calls the frozen metric engine;
- the development path calls the same metric engine;
- no writes or protected/outcome access occurred.

Therefore the gate's independence is currently about artifact/provenance
validation, not formula recomputation.

## Scientific interpretation

A future change in the shared metric implementation could change both the
development result and protected-gate result together while preserving their
mutual agreement, source pins, and hashes. Existing synthetic tests establish
deterministic behavior under the current implementation; they do not provide
an independent semantic oracle for IC, bootstrap, NAV, turnover, pending-order,
or benchmark formulas.

Some target-free artifact-specific verifier scripts in the repository do
perform independent recomputation for particular structural audits. That does
not close this prospective metric-engine question unless the independent
oracle is explicitly bound to the protected evaluation contract.

## Reopen condition and boundaries

Do not alter the evaluator, protected gate, or outcome protocol in this lane.
Reopen only with an explicitly reviewed independent formula oracle or a
versioned verifier contract that separates implementation and semantic review.
Protected H5/H10, hidden OOS/PnL, incumbent comparisons, and real outcome
access remain closed.

Validation: focused probe `1 passed`; standalone probe passed; compilation and
diff checks passed; no provider, production, canonical, capture, cloud,
telemetry, scheduler, or protected state was mutated.

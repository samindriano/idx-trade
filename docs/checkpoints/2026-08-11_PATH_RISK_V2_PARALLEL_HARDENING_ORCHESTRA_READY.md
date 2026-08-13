# Path Risk V2 — Parallel Pre-Outcome Hardening Orchestra Ready

Date: 2026-08-11 (Asia/Jakarta)
Status: **PARALLEL HARDENING AUTHORIZED BEFORE LOCAL DISCOVERY RUN**

Path Risk V2 remains frozen and unviewed on real PR-002/PR-003 F1-F4 outcomes.

The already-implemented V2 stack may now undergo one synthetic/static HEAVY orchestra hardening pass before the local one-shot discovery run.

Root task:

`coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-HARDENING-ORCHESTRA.md`

Five workers are intentionally non-overlapping and own separate new test files:

- W1 PR-002 target/model contract;
- W2 PR-003 person-period/CIF contract;
- W3 fold-specific alpha-only comparator leakage contract;
- W4 runner/provenance/F1-F4 boundary contract;
- W5 frozen gate/selection/spec-consistency contract.

Workers may run concurrently in isolated worktrees. They write tests + handoffs only and may not edit shared production files. MAIN integrates all worker commits, applies any necessary production fix centrally, runs focused/full pytest, and stops before any real V2 execution.

This is a useful orchestra stress test because the five audits are logically independent while all converge on one frozen research runtime.

No worker may access the local V1 model table, raw H10 labels, Path Risk F5/F6, post-2026-07-31 outcomes, or the real V2 output directory.

The final hardening status must be either:

- `PATH_RISK_V2_PARALLEL_HARDENING_PASS_READY_FOR_LOCAL_DISCOVERY`; or
- `PATH_RISK_V2_PARALLEL_HARDENING_BLOCKED_IMPLEMENTATION_DEFECT`.

Only the PASS state returns control to:

`coordination/handoffs/IDX-PATH-RISK-V2-DISCOVERY-F1-F4-RUN.md`.

The frozen alpha ranker, Path Risk V2 spec, candidate definitions, gates, F5/F6 seal, and fresh-forward contract remain unchanged.

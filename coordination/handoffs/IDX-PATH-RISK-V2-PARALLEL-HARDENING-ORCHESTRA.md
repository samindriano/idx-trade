# Handoff: Path Risk V2 Parallel Pre-Outcome Hardening Orchestra

Date: 2026-08-11 (Asia/Jakarta)
Status: **HEAVY PARALLEL PRE-OUTCOME HARDENING — NO REAL PR-002/PR-003 RUN**

## Goal

Exercise the upgraded orchestra on useful, genuinely parallel work before the one-shot local Path Risk V2 discovery run.

Starting point:

- branch: `research/idx-ranking-v2-spec-v1`
- required source state: latest remote HEAD at task start;
- frozen spec: `docs/PATH_RISK_V2_SPEC.md`;
- current implementation: `src/idx_trade/path_risk_v2.py` and `src/idx_trade/path_risk_v2_discovery_run.py`;
- PR-002/PR-003 real F1-F4 outcomes are still unviewed;
- Path Risk F5/F6 and post-2026-07-31 fresh-forward outcomes remain sealed.

This task is **not** the real V2 discovery run. It is an adversarial implementation/research-contract hardening pass using synthetic/static fixtures only.

## Mandatory root reads

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/PATH_RISK_V2_SPEC.md`
4. `docs/checkpoints/2026-08-11_PATH_RISK_V2_IMPLEMENTED_PRE_OUTCOME.md`
5. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
6. `coordination/handoffs/IDX-PATH-RISK-V2-DISCOVERY-F1-F4-RUN.md`

## Orchestra mode

Use **HEAVY** with five independent Luna workers plus MAIN/integrator.

Workers may run concurrently. Writers must use isolated worktrees/branches. Workers do not merge, rebase, push, or spawn nested workers. MAIN alone integrates.

Each worker must verify repository root, branch/base commit, and a clean worktree before editing.

## Parallel worker map

| Worker | Task | Exclusive write ownership |
|---|---|---|
| W1 | PR-002 direct stop-touch classifier hardening | `tests/test_path_risk_v2_pr002_hardening.py`, own handoff only |
| W2 | PR-003 discrete competing-risk/CIF hardening | `tests/test_path_risk_v2_pr003_hardening.py`, own handoff only |
| W3 | alpha-only comparator leakage/incremental-information hardening | `tests/test_path_risk_v2_alpha_comparator_hardening.py`, own handoff only |
| W4 | runner/provenance/F1-F4 boundary/output-contract hardening | `tests/test_path_risk_v2_runner_hardening.py`, own handoff only |
| W5 | frozen gate/selection/spec-consistency audit | `tests/test_path_risk_v2_gate_selection_hardening.py`, own handoff only |

Worker-specific prompts are stored in:

- `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W1-PR002.md`
- `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W2-PR003.md`
- `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W3-ALPHA-COMPARATOR.md`
- `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W4-RUNNER.md`
- `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W5-GATE-SELECTION.md`

## Worker rule: tests first, no shared production edits

Each worker independently audits its assigned contract and writes adversarial tests only in its exclusive test file.

If a worker finds a production-code defect, it must:

1. encode the defect as a failing test where possible;
2. describe the minimal production fix in its handoff;
3. **not edit shared production files**.

This avoids concurrent writes to `path_risk_v2.py` / `path_risk_v2_discovery_run.py` and makes integration/cherry-pick order largely conflict-free.

## MAIN integration phase

After all five workers return:

1. inspect every worker diff and handoff;
2. reject scope creep or duplicate/conflicting tests;
3. integrate worker commits into the root integration worktree;
4. run focused Path Risk V2 tests;
5. run full `python -m pytest`;
6. only MAIN may patch shared production files if an integrated failing test exposes a real contract defect;
7. rerun focused + full tests after any MAIN patch;
8. update one implementation-readiness checkpoint with the final HEAD/test count and defect summary;
9. STOP before any real PR-002/PR-003 F1-F4 execution.

## Important semantic constraints

Do not change:

- PR-002/PR-003 candidate definitions;
- 33-feature set/order;
- H10 stop-touch target;
- competing-risk event convention;
- model hyperparameters;
- F1-F4 development folds;
- F5/F6 seal;
- metrics/gates/selection rule;
- final V3-B ranker;
- fresh-forward contract.

A worker may identify an inconsistency between frozen spec and implementation. MAIN must resolve that as **implementation-to-spec conformance**, not by changing the frozen spec to make code/tests pass.

## Data/outcome prohibition

No worker may open or execute against:

- `path_risk_v1_discovery_model_table.parquet`;
- raw H10 label artifacts;
- F5/F6 Path Risk data;
- any post-2026-07-31 outcome;
- the real V2 discovery output directory.

Synthetic fixtures and repository source/docs only.

## Success condition

The orchestra task succeeds when:

- all five worker handoffs are returned;
- ownership boundaries were respected;
- integrated adversarial tests pass;
- full pytest passes;
- any discovered production defect is fixed by MAIN without changing frozen semantics;
- no real V2 outcome was accessed.

Final status should be one of:

- `PATH_RISK_V2_PARALLEL_HARDENING_PASS_READY_FOR_LOCAL_DISCOVERY`
- `PATH_RISK_V2_PARALLEL_HARDENING_BLOCKED_IMPLEMENTATION_DEFECT`

Only the PASS status allows returning to `IDX-PATH-RISK-V2-DISCOVERY-F1-F4-RUN.md` for the local one-shot run.

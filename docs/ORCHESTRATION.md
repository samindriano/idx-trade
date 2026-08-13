# IDX Trade orchestration

The parent/root thread is `MAIN`, the sole control plane and integrator. The authoritative short project state is `docs/CURRENT_STATUS.md`.

The optimization target is **minimum useful wall-clock time with Luna xhigh concurrency, subject to frozen research gates and integration safety**.

## Operating loop

1. Read `docs/CURRENT_STATUS.md`, newest controlling checkpoint, relevant frozen spec/handoff, and verify actual branch/HEAD/worktree.
2. Freeze decision-changing terms for the current milestone.
3. Build the execution frontier: all useful work that can start now without another unfinished result.
4. Remove overlapping ownership and scientifically dependent future work.
5. Choose DIRECT/LIGHT/HEAVY from the width of the ready frontier.
6. Spawn independent workers before MAIN begins those delegated scopes.
7. MAIN retains cross-cutting architecture, gate protection, blocker resolution, integration prep, and final judgment.
8. Execute concurrently where safe; collect concise evidence-complete handoffs.
9. Verify diffs/tests/provenance/results and record the milestone verdict.
10. Update `docs/CURRENT_STATUS.md` and coordination snapshots when state materially changes.
11. De-escalate when the next frontier becomes sequential.

## Execution levels

| Level | Use when | Coordination pattern |
|---|---|---|
| `DIRECT` | one small or inherently sequential ready path | MAIN works directly + targeted validation |
| `LIGHT` | 2–3 independent ready paths; default for meaningful work | MAIN + 1–3 Luna xhigh workers launched early |
| `HEAVY` | 3–6 independent critical-path paths, broad separable work, uncertain root cause, or decision-changing review | isolated ownership + concurrent workers/reviewer + milestone review |

A substantial task that remains DIRECT must explain why worker startup/coordination would not materially shorten the critical path.

## Parallelism rules

Good parallelism:

- implementation + independent tests + leakage/PIT/provenance audit;
- scorer/backend changes + frontend/API contract work + regression coverage;
- cache/runtime audit + implementation + validation;
- multiple independent root-cause investigations;
- implementation of one frozen research design + independent review.

Bad parallelism:

- duplicate implementation without an explicit comparison purpose;
- overlapping writers;
- opening sealed outcomes early;
- launching a future candidate whose design depends on the current result;
- spawning workers merely because capacity exists.

If MAIN delegates a scope, spawn it before MAIN starts performing the same work.

## Current research state

Alpha architecture search is closed. Final ranker:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

Frozen identifiers:

- model SHA-256: `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`;
- exact 33-feature order SHA-256: `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`.

Path Risk:

- V1 PR-001: failed/closed;
- V2 PR-002/PR-003: frozen + implemented, F1-F4 discovery outcomes unviewed;
- F5/F6: sealed.

Fresh-forward alpha:

- reserve the first exact 100 consecutive H10-mature official signal sessions strictly after 2026-07-31;
- realized forward outcomes remain locked until the explicit one-shot outcome-access boundary.

No automatic calibration, alpha+risk integration, execution-PnL, Kelly, paper/live promotion exists.

## Current Path Risk V2 frontier

Before the evidence-producing run:

- verify current-checkout import resolution;
- run the full repository tests;
- independently confirm the frozen PR-002/PR-003 spec, immutable joined-table identity, F1-F4-only boundary, and F5/F6 seal.

Those read-only/preflight scopes may proceed concurrently if isolated.

Then execute exactly one authorized PR-002/PR-003 F1-F4 discovery run. That final run is sequential because its evidence determines the next scientific decision.

Do not create a new candidate after viewing PR-002/PR-003 merely to rescue the result, and do not touch F5/F6 until a separate one-shot confirmation spec exists.

## Research integrity

Preserve:

`hypothesis -> frozen experiment -> evidence -> compare/prune -> next hypothesis`

Parallelize orthogonal engineering/audit work **inside** the current frozen experiment, not decision-dependent scientific steps across experiments.

Frozen target, candidate definition, folds, holdouts, sources, metrics, thresholds, and acceptance gates do not change post-result merely to improve the verdict.

## Model routing

- User override is authoritative.
- Default MAIN/root: `Luna xhigh`.
- Default workers: `Luna xhigh`.
- `Sol High`: bounded decision-changing checkpoint only.
- HEAVY does not imply Sol.

Useful Sol cases: unresolved architecture conflict after bounded Luna attempts, repeated integration failure, methodology certification, suspiciously strong result, or final high-risk promotion/release review.

## Worker contract

Every delegated task states:

```text
repository/worktree:
base commit:
task id:
parallel group:
role:
question/task:
why this can run now:
owned files/scope:
prohibited changes:
dependencies/assumptions:
deliverable:
validation required:
integration contract:
handoff path:
stopping condition:
```

Workers do not spawn workers. Concurrent writers never share ownership.

## Status freshness

`docs/CURRENT_STATUS.md` overrides older coordination snapshots. At material milestones MAIN should refresh `coordination/TEAM_STATUS.md`, `coordination/TASK_REGISTRY.md`, and material `DECISIONS.md` entries so new agents do not bootstrap from obsolete state.

The separate `codex-orchestra/orchestra/idx-trade` branch must be explicitly resynchronized; it is not automatically updated by source commits.

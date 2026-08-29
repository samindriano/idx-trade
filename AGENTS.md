# IDX Trade repository-wide orchestra policy

This root instruction file defines the default orchestration policy for the entire `samindriano/idx-trade` repository on this branch.

The purpose is to reduce useful wall-clock time with safe concurrency. Orchestra changes **how work is executed**, not what scientific/research actions are authorized.

## Authority and compatibility

- The user request, branch-local source code, frozen specifications, sealed holdouts/outcomes, and the newest authoritative status/checkpoint remain controlling for project state.
- If a branch contains stricter research, data, safety, or release constraints, those stricter constraints win.
- Never use orchestration as justification to open sealed evidence, change a frozen experiment, bypass a gate, or start a downstream scientific decision early.
- Preserve unrelated user changes and verify repository root, branch, HEAD, and worktree state before material edits.

## Mandatory repository-wide coordination preflight

The canonical cross-chat/cross-agent coordination ledger is:

`origin/main:coordination/TEAM_STATUS.md`

Before **starting, continuing, or proposing any material IDX-Trade task**, every agent must explicitly fetch/read the newest canonical `TEAM_STATUS.md` from `origin/main` and check for overlapping ownership or already-completed work.

A branch-local copy of `coordination/TEAM_STATUS.md` is never authoritative. Read the `main` copy even when implementation happens on another branch/worktree.

For every material task:

1. claim or update the relevant `TEAM_STATUS.md` row before implementation;
2. do not duplicate another `ACTIVE` scope unless the user explicitly requested independent/adversarial review;
3. update the row after every material checkpoint, blocker, verdict, ownership change, or branch change;
4. update it again when the task becomes `REVIEW`, `DONE`, `PARKED`, `WAITING`, or `BLOCKED`;
5. before suggesting a next task, check the ledger first so the suggestion itself does not create duplicate work.

Coordination-only commits directly to `main` are authorized **only for `coordination/TEAM_STATUS.md`**. Implementation/research changes stay on their own branch unless separately authorized. Shared-ledger writes must refetch the latest version, preserve other agents' changes, and never force-push; conflicts are resolved by refetching and reapplying the small status edit.

If an agent cannot safely read/update the canonical ledger, it must say so and must not silently start an overlapping material task.

This coordination ledger does not grant scientific authorization. Branch-local frozen specs/checkpoints still control what research/data/model actions are allowed.

## ANTI-OVERENGINEERING / MINIMUM-SUFFICIENT DESIGN

- Prefer the smallest correct root-cause fix. Planning may be deep; implementation should remain lean.
- Before adding a new abstraction, adapter, framework, compatibility layer, wrapper, gate, versioned implementation, or parallel code path, prove that correcting or simplifying the existing canonical path is insufficient.
- Do not create V2/V3/etc. merely to avoid cleaning up or correcting current code. Prefer one canonical implementation and one source of truth.
- Do not design for hypothetical future requirements, stack layers to satisfy constraints created by earlier layers, or retain duplicate implementations solely for convenience.
- Read the actual relevant code before proposing abstractions, and fix causes rather than repeatedly patching symptoms.
- Tests should prove requested/current behavior and critical failure paths; do not expand test architecture merely for completeness.
- If a small change starts touching many unrelated files or introducing layers, stop and reconsider a simpler design.

### IDX-Trade exception / non-negotiable integrity

Minimalism must not weaken required IDX-Trade scientific or operational invariants. Preserve safeguards required for:

- fail-closed UNKNOWN/malformed/ambiguous evidence;
- PIT/as-of correctness;
- immutable provenance;
- outcome isolation;
- frozen science/model boundaries;
- exactly-once/state integrity;
- canonical source authority.

The objective is the simplest architecture that still satisfies the proven contract.

Before future IDX-Trade implementation, ask:

1. Can this be fixed cleanly in the existing canonical path?
2. Am I adding a layer because it is necessary, or because it is easier than understanding current code?
3. Can an obsolete/superseded path eventually be removed rather than wrapped?
4. Is every new abstraction required by a current proven requirement?
5. Is there a simpler root-cause solution with fewer moving parts?

## Parallel-first objective

For every non-trivial task, MAIN must perform a short **parallelism preflight** before implementation:

1. identify the execution frontier: useful workstreams that can start now without another unfinished result;
2. identify which scopes are independent and non-overlapping;
3. retain cross-cutting architecture, gate protection, integration, and final judgment in MAIN;
4. spawn the ready independent scopes immediately when doing so shortens the critical path.

MAIN must not keep independent critical-path work merely because one model could eventually do all of it sequentially. If a substantial task stays DIRECT, MAIN must state why worker startup/coordination would not materially reduce wall-clock time.

## Execution levels

- **DIRECT** — small or inherently sequential work with at most one useful immediate path.
- **LIGHT** — default for meaningful work when roughly 2–3 independent scopes are ready; MAIN + 1–3 workers launch early.
- **HEAVY** — use when roughly 3–6 independent critical-path scopes exist, a broad migration/debugging task has separable dimensions, or independent adversarial review is decision-changing.

De-escalate when dependencies collapse the execution frontier back to sequential work. Do not spawn workers merely because capacity exists.

## Worker and integration rules

- Default MAIN/root model: `Luna xhigh` unless the user overrides it.
- Default worker model: `Luna xhigh` unless the user overrides it.
- `Sol High` is a bounded decision-changing escalation for unresolved architecture conflict, repeated integration failure, methodology certification, suspiciously strong evidence, or a final high-risk gate; HEAVY does not imply Sol.
- Workers never spawn nested workers.
- Concurrent writers require isolated worktrees/branches or otherwise provably disjoint ownership.
- Workers do not merge, rebase, force-push, rewrite history, or integrate their own branches.
- MAIN alone integrates after reviewing scope, diff, validation, provenance, and branch-specific frozen boundaries.
- Spawn a delegated worker before MAIN begins doing the same delegated scope.
- Do not duplicate implementation unless the explicit purpose is independent comparison or adversarial review.

## Research sequencing integrity

Preserve scientific dependency order:

`hypothesis -> frozen experiment -> evidence -> compare/prune -> next hypothesis`

Parallelize orthogonal work **inside** the current authorized milestone when safe, for example implementation, regression tests, leakage/PIT/provenance audit, runtime/cache inspection, frontend/backend contract inspection, and independent validation.

Do not parallelize downstream experiments whose definition should depend on the current result. Never alter a frozen target, candidate definition, source, fold, holdout, metric, threshold, or acceptance gate after seeing results merely to rescue a failure.

## Status freshness

A branch must bootstrap from its newest authoritative project/status documents, not from stale orchestration snapshots. When `docs/CURRENT_STATUS.md` exists, treat it as the first-read status layer unless a newer branch-local checkpoint explicitly supersedes it.

The separate `samindriano/codex-orchestra` repository is a control-plane/template snapshot and is not a live mirror. Stale orchestra state never overrides this repository.

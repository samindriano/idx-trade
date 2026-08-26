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

## Data QA / Research Integrity orchestration mode

When the user asks to **QA, audit, verify, validate, red-team, or trace data/model-input integrity**, treat it as a dedicated integrity workflow rather than an ordinary implementation task.

Read `docs/research_integrity/DATA_QA_ORCHESTRATION_V1.md` and `docs/research_integrity/RESEARCH_INTEGRITY_DATA_QA_GATE_V1.md` when they exist on the active branch.

### Default execution shape

Use `HEAVY` by default for market-wide, lineage-wide, model-impacting, or decision-changing integrity audits. Use `LIGHT` only for genuinely bounded scopes. Use `DIRECT` only when there is no useful independent audit frontier.

For a material QA task, MAIN should allocate independent lanes covering as applicable:

1. **source semantics / data contract** — meaning, unit, source authority, adjustment basis, publication/revision semantics;
2. **structural / coverage integrity** — schema, keys, calendar, listing/tradability, missingness, value identities;
3. **PIT / causality / provenance** — knowledge time, decision cutoff, leakage, revision lineage, immutable hashes;
4. **economic / event semantics** — CA, adjustment logic, share-count events, suspensions, listings/delistings, event-specific behavior;
5. **anomaly / distribution census** — search for unexplained extremes and regime breaks rather than checking only expected cases;
6. **independent recomputation / blast radius** — recompute critical quantities through an implementation independent of the possibly faulty production helper and trace exact downstream identities;
7. **adversarial falsification** — actively try to prove the suspected bug harmless and try to falsify any proposed remediation.

The same worker should not both establish a decision-changing ground-truth claim and certify its independent falsification when independent capacity is available.

### Integrity-specific safety

Unless separately authorized by the user and controlling scientific contracts, a QA task does **not** authorize:

- protected outcome/holdout access;
- model tuning or refit;
- frozen-science modification;
- prospective counter mutation/reset;
- retroactive trade/fill creation;
- production capture/runtime activation;
- production provider writes;
- treating ambiguous evidence as a pass.

### Fail-closed verdict rule

Use the Research Integrity Gate vocabulary. For any required check:

`PASS` may proceed; `FAIL` blocks; `UNKNOWN` also blocks.

A missing required check must be materialized as `UNKNOWN`, never silently omitted.

### Incident conversion rule

A confirmed integrity defect is not closed merely because rows/code were fixed. Closure requires:

- root cause;
- bounded blast radius;
- remediation/quarantine verification when authorized;
- a permanent invariant or golden/adversarial case;
- an automated regression test where feasible;
- independent red-team confirmation;
- re-run of the controlling gate.

The objective is that a bug class discovered once becomes materially harder to reintroduce silently.

### MAIN owns final judgment

Workers produce evidence. MAIN owns scope protection, reconciliation, materiality judgment, final gate verdict, and whether remediation is actually authorized.

## Status freshness

A branch must bootstrap from its newest authoritative project/status documents, not from stale orchestration snapshots. When `docs/CURRENT_STATUS.md` exists, treat it as the first-read status layer unless a newer branch-local checkpoint explicitly supersedes it.

The separate `samindriano/codex-orchestra` repository is a control-plane/template snapshot and is not a live mirror. Stale orchestra state never overrides this repository.

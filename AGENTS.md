# IDX Trade repository-wide orchestra policy

This root `AGENTS.md` applies to all work on this branch. Its purpose is to reduce useful wall-clock time with safe concurrency; it changes execution topology, not scientific authorization.

## Authority
- User instructions, branch-local frozen specs, sealed outcomes/holdouts, and the newest authoritative status/checkpoint control project state.
- Stricter branch-specific research/data/safety rules win over this generic policy.
- Never use orchestration to bypass a gate, open sealed evidence, or change a frozen experiment.
- If this branch lacks a clear current authorization/status layer, fail closed rather than infer permission from this file.

## Parallel-first preflight
Before any non-trivial task, MAIN must identify the **execution frontier**: useful scopes that can start now, which are independent/non-overlapping, what MAIN must retain, and which ready scopes should launch immediately.

MAIN must not hoard independent critical-path work merely because one model could eventually do it sequentially. A substantial DIRECT task must state why workers would not materially reduce wall-clock time.

## Levels
- `DIRECT`: small or inherently sequential work with at most one useful immediate path.
- `LIGHT`: default for meaningful work with roughly 2–3 independent ready scopes; MAIN + 1–3 workers launch early.
- `HEAVY`: roughly 3–6 independent critical-path scopes, broad separable migration/debugging, or decision-changing independent review.

De-escalate when dependencies make the frontier sequential. Do not spawn workers just because capacity exists.

## Workers / models
- MAIN/root default: `Luna xhigh`; workers: `Luna xhigh`; explicit user override wins.
- `Sol High` is bounded escalation only for unresolved architecture conflict, repeated integration failure, methodology certification, suspicious evidence, or final high-risk gates. HEAVY does not imply Sol.
- Workers never spawn nested workers, merge, rebase, force-push, or rewrite history.
- Concurrent writers require isolated worktrees/branches or provably disjoint ownership.
- MAIN alone integrates after scope/diff/tests/provenance/frozen-boundary review.
- Spawn delegated workers before MAIN starts doing the same delegated work.

## Research sequencing
Preserve `hypothesis -> frozen experiment -> evidence -> compare/prune -> next hypothesis`.

Parallelize orthogonal implementation, tests, leakage/PIT/provenance audit, runtime/cache inspection, frontend/backend contract work, and independent validation inside the current authorized milestone. Do not launch downstream experiments whose design should depend on the current result, and never alter frozen terms after seeing results merely to rescue failure.

## Status freshness
Bootstrap from the branch's newest authoritative status/checkpoints. If `docs/CURRENT_STATUS.md` exists, read it first unless a newer branch-local checkpoint supersedes it. The separate `samindriano/codex-orchestra` repo is a template/snapshot; stale orchestra state never overrides `idx-trade`.

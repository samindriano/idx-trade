# Repository Hygiene V2 — Aggressive Consolidation Policy

Date: 2026-08-22 Asia/Jakarta
Status: `PREPARED_PLAN_ONLY_DESTRUCTIVE_APPLY_NOT_YET_RUN`
Base main at preparation: `0f5ae68ff113264513ed4c96e452cc2688e4de16`

## Why V2 exists

Repository Hygiene V1 was intentionally conservative. Its branch snapshot contained 138 remote branches. The fresh 2026-08-22 inventory now contains 273 remote branches. A 30–40 branch reduction is no longer sufficient: branch/PR clutter is obscuring the current production/research lineage and materially increases the risk that a future agent continues an obsolete experiment.

V2 therefore optimizes for a small, legible repository while preserving scientific memory.

## Preservation principle

Code and insight are preserved differently.

- `KEEP_CANONICAL`: current E2E/prospective/runtime code or a still-live research/data lane. Keep branch.
- `KEEP_ANCHOR`: a final scientific or architectural anchor whose exact code remains materially reusable. Keep branch.
- `ARCHIVE_TAG_THEN_DELETE`: exact historical code is still useful for forensic reproduction, but it does not deserve a live branch. Create an immutable archive tag at the exact branch HEAD, then delete the branch.
- `TOMBSTONE_THEN_DELETE`: the durable value is the result/lesson rather than the implementation. Record branch name, exact HEAD, verdict, important metrics and why it was superseded/rejected in the tombstone ledger, then delete the branch without a live archive branch.
- `DELETE_REDUNDANT`: intermediate audit/remediation/prereg/checkpoint branches whose unique value is already captured by a retained descendant, archive tag, PR history, or tombstone. Delete after exact-head preflight.

The goal is approximately **50–70 live branches** after cleanup, not another conservative 200+ branch repository.

## Hard safety rules

1. `main` can never be deleted.
2. Cleanup V2 itself remains protected until the cleanup result is audited.
3. The cleanup tool is two-phase: `plan` then separately authorized `apply`.
4. The plan records exact remote branch HEAD SHA for every branch.
5. Apply must fail closed if `origin/main` or any branch-to-delete moved since the plan.
6. High-value historical branches listed as archive candidates must have their archive tags pushed successfully before any branch deletion starts.
7. Apply never edits working-tree files, merges branches, rebases history, resets local branches, or changes scientific artifacts.
8. Branch deletion does not authorize reopening rejected experiments.
9. Open PRs for obsolete Decision/research lineages are closed separately before destructive branch cleanup; active Stockbit operational PRs remain open.
10. New branches created after the frozen plan are untouched.

## Canonical scientific state after cleanup

### Alpha/model

- Clean historical production/research parent: V2 `HGB_XS_MARKET` under the clean V4-X1 lineage.
- Historical V3-B/O2 contamination conclusions remain recorded; O2 is not a production parent.
- V4-X1 clean prospective scoring remains the prospective scorer lineage.

### Decision

- `Decision V2` is the incumbent.
- Decision V3 is rejected.
- Decision V4 Refill Decoupling is structurally rejected.
- Decision research is closed on the consumed development set.
- No V4.1/V4.2/rescue threshold search is authorized.

### Downstream E2E

The next system objective is E2E Baseline Paper V1: clean prospective score -> Decision V2 -> frozen sizing/execution -> CA-aware persistent paper state -> restart-safe orchestration.

### Historical experiments

Failed/blocked/superseded experiments remain queryable through:

1. canonical docs/checkpoints that survive in retained descendants;
2. GitHub PR history, even after PR closure;
3. `EXPERIMENT_TOMBSTONES_V2.md`;
4. archive tags only for the small subset where exact historical source code remains worth preserving.

## What V2 intentionally does not preserve as live branches

Examples include:

- every Decision prereg/implementation/audit/diagnosis runner after Decision closure;
- Stage 3/4/4B/5 intermediate research branches superseded by later ranking lineage;
- historical Open recovery attempts that did not become the canonical execution source;
- repeated Zapi/Yahoo/TradingView/Open residual audits whose conclusions are already known;
- intermediate corporate-action schedule/event forensic branches once their conclusions were incorporated into the clean/continuity lineage;
- repeated review-only branches after the accepted result is captured;
- placeholders/noop branches;
- old frontend versions superseded by the current monitoring refresh.

This is deliberate. A branch is not the unit of scientific memory; durable conclusions are.

## Execution boundary

Preparation of this policy/config/cleanup utility is not destructive cleanup authorization.

Required sequence:

1. close obsolete PRs;
2. run `repository_hygiene_v2.py plan` locally against fresh `origin/*` refs;
3. return the generated plan JSON + counts to ChatGPT;
4. independently review every KEEP/archive family and deletion count;
5. only then authorize `apply` with the exact plan SHA-256 and confirmation token;
6. recount remote branches and verify retained anchors;
7. freeze a final cleanup result checkpoint.

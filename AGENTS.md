# IDX Trade V0 working agreement

## Canonical project memory

`docs/CURRENT_STATUS.md` is the **first-read authoritative status layer**. It records the latest approved phase, branch, frozen hashes, runtime gate, holdout state, and next authorization boundary. When older bootstrap text conflicts with it, the newer `CURRENT_STATUS` plus the newest controlling checkpoint wins.

`docs/PROJECT_CONTEXT_MASTER.md` is the comprehensive bootstrap/history layer for new chats, model handoffs, and context-window loss.

`docs/PROJECT_LEDGER.md` is the canonical chronological causal ledger preserving failure -> diagnosis -> fix -> validation history.

Before any material DATA, VALIDATION, MODEL, RUNTIME, or WEB task, read in this order:

1. `docs/CURRENT_STATUS.md`;
2. newest relevant checkpoint under `docs/checkpoints/`;
3. relevant frozen spec/handoff;
4. `docs/PROJECT_CONTEXT_MASTER.md` when broader history is needed;
5. `docs/PROJECT_LEDGER.md` when causal chronology matters.

Then verify the actual current branch/HEAD and worktree state before acting.

Do not delete failed approaches from continuity records merely because they were fixed. Failure history is part of the research knowledge and prevents repeated mistakes after handoff/context loss.

## Repository-wide principles

This repository is **EXPLORATORY_RESEARCH_ONLY**. It is not investment advice and must never silently become a live trading system.

- Do not fabricate market data, performance, rankings, scores, model state, tests, or completed work.
- Do not silently substitute a provider, rewrite historical artifacts, or infer exchange state from missing provider rows.
- Unknown lineage, provenance, point-in-time identity, timing, entitlement, or session coverage fails closed when decision-changing.
- Keep raw OHLC execution prices separate from adjusted/vendor information.
- Preserve existing IDX source contracts, tests, frozen research specifications, and unrelated user changes.
- Never commit credentials, private runtime data, generated model artifacts, caches, or user-specific local paths.
- Workers edit only their owned scope. Concurrent writers require isolated worktrees or provably disjoint ownership.
- Workers never spawn workers, merge, rebase, force-push, or rewrite history.

## Current authoritative research state

The exact current state remains controlled by `docs/CURRENT_STATUS.md`. As of the 2026-08-11 synchronized checkpoint:

- alpha architecture search: **CLOSED**;
- final historical-development ranker: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- final V3-B refit: **FROZEN SUCCESSFULLY**;
- model SHA-256: `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`;
- exact 33-feature order SHA-256: `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- V3/V4 alpha exploration is closed; do not reopen it automatically;
- Path Risk V1 PR-001: failed/closed and may not be rescued;
- Path Risk V2 PR-002/PR-003: frozen + implemented, F1-F4 discovery outcomes not yet viewed;
- Path Risk F5/F6: sealed;
- post-2026-07-31 fresh-forward realized outcomes: locked/unaccessed;
- calibration, alpha+risk integration, execution-PnL, Kelly, paper/live: not automatically authorized.

## Parallel-first orchestration objective

The user uses Luna xhigh orchestration primarily to **reduce wall-clock time through useful concurrency**. Correctness and research integrity remain hard constraints, but meaningful work should not default to one Luna doing every independent scope sequentially.

The parent/root thread is `MAIN`, the sole decomposer, integrator, and phase-transition authority.

### Mandatory parallelism preflight

Before substantial implementation/research work, MAIN must identify:

1. **execution frontier:** useful workstreams that can start now without another unfinished result;
2. **independence:** which scopes have non-overlapping ownership and do not depend on another scientific decision;
3. **MAIN-retained work:** cross-cutting architecture, coupling, gate protection, integration, or final judgment;
4. **spawn set:** ready independent scopes that should launch immediately.

Rules:

- MAIN must not hoard independent critical-path work merely because it can eventually finish it alone.
- Spawn workers before MAIN starts doing the same delegated scope.
- Do not manufacture parallelism by splitting tightly coupled edits into artificial fragments.
- Do not duplicate implementation unless the explicit purpose is independent comparison/adversarial review.
- A substantial task that remains DIRECT must state why workers would not materially shorten wall-clock time.

### Execution levels

- `DIRECT`: small or inherently sequential work with at most one useful immediate path.
- `LIGHT`: **default for meaningful work**; MAIN + 1–3 Luna xhigh workers when roughly 2–3 independent scopes are ready now.
- `HEAVY`: MAIN + 3–6 Luna xhigh workers/reviewer when at least three independent critical-path workstreams exist, root cause is broad/uncertain, or independent review is decision-changing.

De-escalate when dependencies collapse the execution frontier back to sequential work.

### Typical useful IDX parallelism

Parallelize when safe:

- implementation + independent regression tests + leakage/PIT/provenance audit;
- model/runtime implementation + cache/performance inspection;
- scorer/backend work + frontend/API contract inspection + validation coverage;
- multiple independent root-cause investigations during debugging;
- implementation of one frozen experiment + independent methodology/result audit.

Do not parallelize decision-dependent scientific steps merely for speed.

## Research sequencing integrity

Preserve:

`hypothesis -> frozen experiment -> evidence -> compare/prune -> next hypothesis`

Do not launch a downstream candidate before the current result when its definition should depend on that result.

Within the current frozen experiment, however, implementation, tests, audit, provenance inspection, runtime preparation, and independent validation may proceed concurrently if ownership and evidence boundaries are clean.

Never change a frozen target, source, candidate definition, fold, holdout, metric, threshold, or acceptance gate after seeing results merely to rescue a failure.

## Current Path Risk V2 hard boundary

Immediate next action remains:

1. verify current-checkout import resolution and run the full repository test suite;
2. if preflight passes, execute exactly one frozen Path Risk V2 PR-002/PR-003 F1-F4 development run using `coordination/handoffs/IDX-PATH-RISK-V2-DISCOVERY-F1-F4-RUN.md`;
3. review the result against the frozen V2 gate;
4. do not touch F5/F6 until a separate one-shot confirmation specification exists.

The final evidence-producing discovery run is intentionally serialized after preflight. Supporting read-only audit/test diagnosis may run in parallel if it cannot contaminate or redefine the run.

Do not:

- reopen/modify the final V3-B alpha architecture automatically;
- rescue/rewrite PR-001;
- add PR-004 after seeing PR-002/PR-003;
- access Path Risk F5/F6 during V2 discovery;
- use F5/F6 to choose PR-002 vs PR-003;
- access/summarize post-2026-07-31 fresh-forward realized outcomes early;
- create risk-veto, reranking, sizing, execution-PnL, paper/live rules automatically.

## Model routing

The user may override this at any time.

- persistent Codex MAIN/root default: `Luna xhigh`;
- normal worker default: `Luna xhigh`;
- escalation model: `Sol High` for bounded decision-changing checkpoints only.

Use Sol High for unresolved architecture conflict after bounded Luna attempts, repeated integration/debugging failure, methodology certification, suspiciously strong research evidence, or final high-risk promotion/release review.

HEAVY does not imply Sol. Buy safe speed with Luna concurrency before using a persistent premium root.

## Roles and ownership

| Role | Typical ownership |
|---|---|
| EXPERIMENT / RESEARCH | bounded hypotheses/specs, experiment implementation and interpretation; no silent gate changes |
| VALIDATION | tests, leakage/PIT audit, evaluation integrity, sealed-fold/outcome controls, adversarial result review |
| DATA | providers, identity/tradability, point-in-time universe, coverage, source/provenance contracts |
| PRODUCTION | data/runtime/storage architecture, artifact contracts, scorer/runtime integration |
| WEB | monitoring/API/frontend work when explicitly scoped; locked outcomes must remain inaccessible |

MAIN alone integrates branches and edits shared coordination state.

## Worker task contract

Every worker prompt must state:

- exact repository/worktree and base commit;
- task ID and parallel group;
- role and one bounded question;
- why the task can run now;
- owned files/scope and prohibited changes;
- satisfied dependencies/assumptions;
- deliverable and required validation;
- integration contract;
- handoff path and stopping condition.

Every delegated task concludes with a concise decision-complete handoff under `coordination/handoffs/`.

## Coordination/status freshness

Within this repository, `docs/CURRENT_STATUS.md` is authoritative over older `coordination/TEAM_STATUS.md` or task-registry snapshots. MAIN should keep coordination files synchronized at material milestones so executing agents do not bootstrap from obsolete state.

The separate `samindriano/codex-orchestra` project branch is also a snapshot, not a live mirror. A source milestone may require an explicit orchestra resync; stale orchestra state never overrides this repository.

## Git safety

- Verify exact repo root, branch, HEAD, and worktree state before edits.
- Preserve unrelated user changes; no hard reset, clean, force push, rebase, or history rewrite unless explicitly authorized.
- MAIN integrates only after checking scope, diff, tests/validation, provenance, and frozen boundaries.
- Runtime market data, credentials, generated models, and local caches stay out of Git.

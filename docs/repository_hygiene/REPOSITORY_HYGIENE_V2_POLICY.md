# Repository Hygiene V2 — Aggressive Consolidation Policy

Date: 2026-08-22 Asia/Jakarta
Status: `REVISED_PLAN_REQUIRED_DESTRUCTIVE_APPLY_NOT_YET_RUN`
Original preparation main: `0f5ae68ff113264513ed4c96e452cc2688e4de16`

## Why V2 exists

Repository Hygiene V1 was intentionally conservative. Its branch snapshot contained 138 remote branches. The fresh 2026-08-22 V2 dry-run contains 274 remote branches. A 30–40 branch reduction is no longer sufficient: branch/PR clutter obscures the current production/research lineage and materially increases the risk that a future agent continues an obsolete experiment.

V2 therefore optimizes for a small, legible repository while preserving scientific memory. The revised target is approximately **50 live branches**, not 200+.

## Preservation principle

Code and insight are preserved differently.

- `KEEP_CANONICAL`: current E2E/prospective/runtime code or a still-live research/data lane. Keep branch.
- `KEEP_ANCHOR`: a final scientific or architectural anchor whose exact code remains materially reusable. Keep branch.
- `ARCHIVE_TAG_THEN_DELETE`: exact historical code is still useful for forensic reproduction, but it does not deserve a live branch. Create an immutable lightweight archive tag at the exact branch HEAD, then delete the branch.
- `TOMBSTONE_THEN_DELETE`: the durable value is the result/lesson rather than the implementation. Record the conclusion and key evidence in durable docs/PR history, then delete the branch.
- `DELETE_REDUNDANT`: intermediate audit/remediation/prereg/checkpoint branches whose unique value is already captured by a retained descendant, archive tag, PR history, or tombstone. Delete after exact-head preflight.

A branch is not the unit of scientific memory. The retained unit may instead be a canonical descendant, a final acceptance tag, a tombstone, a PR record, or a frozen external artifact hash.

## Revised retention boundary

The first V2 dry-run proposed 66 live branches, 20 archive tags, and 188 tombstone deletions. Independent review found that 66 was still too conservative for the E2E-first objective.

The revised allowlist targets **50 live branches**. Important historical or acceptance-only heads removed from the live set are promoted to archive tags rather than silently discarded. Examples include final TradingView semantic anchors, old PIT-sector/market-breadth/KSEI source lanes, selected integrity audits, the Decision V2 accepted implementation audit, and final Financial/Foreign-Flow/Price-State acceptance heads.

Branches fully contained by a retained descendant do not need an archive tag merely because they once existed. Examples include the original Stockbit intraday capture parent, the prior Stockbit Stream routine-remediation branch, and the pre-freeze clean-data consolidation parent.

## Hard safety rules

1. `main` can never be deleted.
2. Cleanup V2 itself remains protected until the cleanup result is audited.
3. The cleanup tool is two-phase: `plan` then separately authorized `apply`.
4. Every plan records the exact remote HEAD SHA for every branch and the exact `origin/main` SHA.
5. Apply must fail closed if `origin/main`, any retained branch, or any branch-to-delete moved since the plan.
6. Selected historical code anchors use deterministic lightweight archive tags at their exact branch HEADs.
7. The exact plan JSON is preserved in a deterministic annotated tag named `archive/hygiene-v2/deletion-plan-<plan-sha-prefix>` targeted at the frozen `origin/main` commit.
8. **All new archive tags, the deletion-plan tag, and all branch deletions are submitted in one `git push --atomic` remote transaction.** The remote must accept every ref update or none of them.
9. If the remote cannot support/accept the full atomic transaction, cleanup stops. The script must not silently batch or degrade to partial deletion.
10. Apply never edits working-tree scientific files, merges branches, rebases history, resets local branches, or changes runtime artifacts.
11. New branches created after a frozen plan are untouched because they are absent from that plan.
12. Branch deletion does not authorize reopening rejected experiments.
13. Open PRs for obsolete Decision/research lineages are closed separately before destructive branch cleanup; active Stockbit operational PRs remain open.
14. A successful remote push is followed by independent verification of every archive tag, the deletion-plan tag, every deleted branch, and every retained branch.

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

### Sizing / execution / CA

Sizing V1 and Execution V1 are not separate missing research lanes. Their implementation is already present in the retained `integration/forward-ca-attestation-v1` downstream lineage, together with dividend execution/runtime and persistent CA-aware paper-state foundations. Old intermediate sizing/execution branches therefore do not need to remain live merely to preserve source code.

### Downstream E2E

The next system objective after cleanup is E2E Baseline Paper V1:

`clean prospective score -> Decision V2 -> fixed sizing -> Execution V1 -> CA-aware persistent paper state -> restart-safe orchestration`.

### Active operational exceptions

Stockbit Stream PR #35 (`fix/stockbit-stream-zapi-envelope-v1`) and adversarial PR #36 (`audit/stockbit-stream-v2-red-team-v1`) remain live and are explicitly retained. Stockbit intraday post-close remediation remains live. Hygiene must not close or delete these active operational heads.

### Historical experiments

Failed/blocked/superseded experiments remain queryable through:

1. canonical docs/checkpoints that survive in retained descendants;
2. GitHub PR history, even after PR closure;
3. `EXPERIMENT_TOMBSTONES_V2.md`;
4. archive tags for the subset where exact historical source code remains worth preserving;
5. the annotated deletion-plan tag, which preserves the exact branch-to-SHA disposition map used by destructive cleanup.

## What V2 intentionally does not preserve as live branches

Examples include:

- every Decision prereg/implementation/audit/diagnosis runner after Decision closure;
- Stage 3/4/4B/5 intermediate research branches superseded by later ranking lineage;
- historical Open recovery attempts that did not become the canonical execution source;
- repeated Zapi/Yahoo/TradingView/Open residual audits whose conclusions are already known;
- intermediate corporate-action schedule/event forensic branches once their conclusions were incorporated into the clean/continuity lineage;
- repeated review-only branches after their accepted result is represented by a retained descendant or archive tag;
- placeholders/noop branches;
- old frontend versions superseded by the current monitoring refresh;
- ancestor branches fully contained in a retained operational descendant.

This is deliberate. Durable conclusions and exact selected anchors survive; branch clutter does not.

## Execution boundary

Preparation/revision of this policy, config and cleanup utility is **not** destructive cleanup authorization.

Required sequence:

1. obsolete PRs are closed; active Stockbit PR #35/#36 remain open;
2. regenerate `repository_hygiene_v2.py plan` against fresh remote refs using the revised config;
3. return the new plan SHA, exact counts, KEEP list, archive list and safety checks to ChatGPT;
4. independently audit the revised plan, especially false-delete risk and open-PR heads;
5. only then authorize one exact `apply` using that plan SHA and confirmation token;
6. the apply must use one atomic remote push;
7. recount remote branches and verify all retained heads/archive tags/deletion-plan tag;
8. freeze a final cleanup result checkpoint;
9. update canonical `TEAM_STATUS`/roadmap and create the single E2E baseline lineage.

The first dry-run plan SHA `d189aa943754beecfea486db2d3b8d26c5b5780404a0378c31d1bfea66756603` is obsolete and **must never be applied** after this revision.

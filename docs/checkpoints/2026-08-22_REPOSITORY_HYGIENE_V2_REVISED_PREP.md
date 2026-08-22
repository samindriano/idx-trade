# Repository Hygiene V2 — Revised Aggressive Preparation

Date: 2026-08-22 Asia/Jakarta
Status: `REVISED_PREP_COMPLETE_NEW_DRY_RUN_REQUIRED_DESTRUCTIVE_APPLY_NOT_AUTHORIZED`

## First dry-run reviewed

Reviewed hygiene branch HEAD:
`899cb1da9689d838f9ed44242cfac19889d88a6f`

First dry-run plan SHA-256:
`d189aa943754beecfea486db2d3b8d26c5b5780404a0378c31d1bfea66756603`

Observed first plan:
- remote branches: 274;
- KEEP: 66;
- ARCHIVE_TAG_THEN_DELETE: 20;
- TOMBSTONE_THEN_DELETE: 188;
- estimated live after cleanup: 66;
- missing configured KEEP: 0;
- missing configured ARCHIVE: 0;
- critical protection checks: PASS;
- destructive apply: NOT RUN.

The first plan is now **OBSOLETE AND MUST NOT BE APPLIED** because the retention policy and apply implementation were revised after independent review.

## Independent review findings

No critical live E2E/Stockbit/Decision branch was found in the first plan's delete set. However, the review deliberately tightened both retention and destructive safety.

### Retention tightening

The live target was reduced from 66 to approximately 50 branches.

Branches removed from live retention fall into two classes:

1. historical/acceptance heads with meaningful forensic value -> promote to `ARCHIVE_TAG_THEN_DELETE`;
2. ancestors fully contained by retained descendants -> allow tombstone/redundant deletion without a new archive tag.

Examples of contained ancestors:
- `data/stockbit-intraday-forward-capture-v1` is contained by `fix/stockbit-intraday-postclose-fix-v1`;
- `fix/stockbit-stream-routine-remediation-v1` is contained by open PR #35 head `fix/stockbit-stream-zapi-envelope-v1`;
- `data/v4-x-clean-data-consolidation-v1` is contained by `data/v4-x-clean-data-consolidation-v1-final-input-freeze-v1`.

### E2E code preservation audit

`integration/forward-ca-attestation-v1` was inspected and directly contains the downstream implementation required for future E2E integration, including:
- Sizing V1;
- Execution V1 engine, allocator, contract and verifier;
- dividend execution/runtime;
- persistent CA-aware state foundations;
- canonical EOD/CA attestation support.

Therefore historical sizing/execution branches are not required to remain live solely to preserve source code.

### Decision V2 acceptance preservation

The accepted remediated Decision V2 code HEAD `32af46172a686fdf407e1026ad4acdab12edc355` is an ancestor of retained branch `research/idx-decision-v2-minimal-implementation-v1`. The separate acceptance audit branch is promoted to an archive tag so its exact review checkpoint remains recoverable without remaining live.

### Active PR verification

GitHub connector independently verified:
- PR #35 remains OPEN, head `fix/stockbit-stream-zapi-envelope-v1`;
- PR #36 remains OPEN/DRAFT, head `audit/stockbit-stream-v2-red-team-v1`.

Both heads remain explicit KEEP branches. Local `gh` authentication failure in the first Codex dry-run is therefore non-blocking.

## Destructive safety hardening

The original apply implementation pushed archive tags first and branch deletions second. That was rejected as insufficiently atomic for a >200-ref cleanup.

Revised apply contract:
- exact plan SHA required;
- exact `origin/main` required;
- every KEEP and deletion-candidate branch must still match its frozen plan HEAD;
- archive tags are deterministic lightweight tags, created via `git update-ref`;
- the exact plan JSON is stored verbatim in an annotated deletion-plan tag;
- all new archive tags + deletion-plan tag + every branch deletion are sent in one `git push --atomic` transaction;
- if the remote cannot accept the entire atomic ref transaction, stop with zero intentional remote mutation; do not batch;
- post-push verification checks archive tags, plan tag, deleted refs and retained refs;
- no scientific/runtime artifact mutation is authorized.

Regression tests were added to lock the atomic-push, lightweight-tag and verbatim-plan-tag invariants.

## Revised expected shape

Given the same 274-branch remote inventory, the revised config should produce approximately:
- KEEP: 50;
- ARCHIVE_TAG_THEN_DELETE: 45;
- TOMBSTONE_THEN_DELETE: 179;
- live after cleanup: 50.

These are expectations only. The next fresh dry-run is authoritative and may differ if remote refs move.

## Authorization boundary

Current authorization is **PLAN/VALIDATION ONLY**.

Not authorized:
- remote tag creation;
- branch deletion;
- applying the obsolete first plan;
- applying any newly generated plan before independent review;
- merging/rebasing/resetting live lineages;
- closing PR #35/#36.

Next action: local Codex validates the revised exact branch HEAD, runs focused hygiene tests, generates a new plan only, and returns its exact SHA/counts/lists for independent audit.

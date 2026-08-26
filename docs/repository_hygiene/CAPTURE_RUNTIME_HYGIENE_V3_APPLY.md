# Capture Runtime Hygiene V3 — Atomic Apply Contract

Date: 2026-08-26 Asia/Jakarta
Status: `DOCUMENTATION_REVIEW_AND_CI_REQUIRED_BEFORE_APPLY`

This file is an execution contract for a future local/API-capable Git ref cleanup. It does **not** authorize changing runtime data, schedulers, workflows, R2, models, outcomes, counters, or Windows tasks.

## Preconditions

Do not run the destructive ref update unless all are true:

1. PR #94 (Capture Runtime Registry V1) is merged to `main` and exact-head CI passed.
2. `origin/main` contains `docs/repository_hygiene/CAPTURE_RUNTIME_REGISTRY_V1.md`.
3. PR #36 / `audit/stockbit-stream-v2-red-team-v1` is untouched by this apply.
4. `fix/stockbit-intraday-postclose-fix-v1`, `ops/e2e-paper-cloud-launcher-v1`, and `integration/idx-e2e-baseline-paper-v1` are untouched.
5. Every source branch below still resolves to the audited expected SHA. Any mismatch is a hard stop; re-audit instead of force-deleting.
6. Default-branch workflow files and accepted pinned implementation SHA are recorded before mutation.

## Exact unique heads to archive permanently

Create annotated tags at these exact commits before deleting their source branches:

| Permanent tag | Exact commit | Source branch |
|---|---|---|
| `archive/capture-hygiene-v3/forward-open-scaffold-dc5e84b5-tag` | `dc5e84b589eebe040119f48f9f69538d398a9d36` | `ops/idx-forward-open-archive-v1` |
| `archive/capture-hygiene-v3/stockbit-v1-base-009be16e-tag` | `009be16e5db8a7a9899cff73f10f53dfc8a3fe6c` | `data/stockbit-stream-prospective-archive-v1` |
| `archive/capture-hygiene-v3/stockbit-observable-smoke-17803978-tag` | `17803978c1e145dbe084c828e45bed5247c13aa6` | `ops/stockbit-stream-observable-smoke-v1` |
| `archive/capture-hygiene-v3/market-index-eod-8c94f56b-tag` | `8c94f56b0025ad68b254476aaddb73be81bfb0bc` | `data/market-index-forward-eod-v1-monitoring` |

Temporary exact-head branch refs currently exist for the same four commits:

- `archive/capture-hygiene-v3/forward-open-scaffold-dc5e84b5`
- `archive/capture-hygiene-v3/stockbit-v1-base-009be16e`
- `archive/capture-hygiene-v3/stockbit-observable-smoke-17803978`
- `archive/capture-hygiene-v3/market-index-eod-8c94f56b`

These temporary branches are only a connector workaround. Delete them after permanent tag verification.

## Merged / contained source branches certified for deletion

Before deletion, verify each branch is still contained in the stated live lineage or its merged PR remains reachable:

- `ops/idx-official-open-r2-cloud-capture-v1` — PR #90 merged.
- `ops/idx-official-open-cloud-scheduler-v1` — PR #91 merged to `main`.
- `integration/e2e-cloud-first-orchestration-v1` — PR #92 merged to accepted E2E integration.
- `integration/forward-eod-automation-monitoring` — contained by accepted E2E lineage.
- `integration/v4-x1-eod-auto-score-v1` — contained by accepted E2E lineage.
- `fix/stockbit-stream-zapi-envelope-v1` — PR #35 merged.
- `fix/stockbit-stream-daily-capture-v1` — PR #72 merged.
- `fix/stockbit-stream-transient-reliability-main-v1` — PR #79 merged.
- `fix/stockbit-stream-schema-diagnostics-v1` — PR #81 merged.
- `fix/stockbit-r2-retention-v1` — retention remediation/closure merged.

No extra archive tag is required solely to preserve those branch heads because their accepted changes/history remain reachable through merged/current history. If a preflight unexpectedly finds unique commits, stop and reclassify the branch instead of deleting it.

## Protected refs — explicit deny list

Never delete or move these as part of this apply:

- `main`
- `integration/idx-e2e-baseline-paper-v1`
- `ops/e2e-paper-cloud-launcher-v1`
- `fix/stockbit-intraday-postclose-fix-v1`
- `audit/stockbit-stream-v2-red-team-v1`
- current E2E/R2 input-provisioning worktree branch
- any unrelated research/data branch.

## Suggested local preflight

Run from a clean checkout with no credentials printed:

```bash
git fetch origin --prune --tags

git rev-parse origin/ops/idx-forward-open-archive-v1
git rev-parse origin/data/stockbit-stream-prospective-archive-v1
git rev-parse origin/ops/stockbit-stream-observable-smoke-v1
git rev-parse origin/data/market-index-forward-eod-v1-monitoring
```

The outputs must exactly equal the four audited SHAs above.

For the ten merged/contained branches, verify containment/merged provenance individually. For ancestry-based branches use `git merge-base --is-ancestor <branch-head> <accepted-live-ref>`; for merged PR heads verify the merged PR/merge commit remains reachable. Do not reduce the checks to branch-name matching.

Record before mutation:

```bash
git rev-parse origin/main
git show origin/main:.github/workflows/stockbit-stream-prospective-capture.yml > <temporary-before-file>
git show origin/main:.github/workflows/official-open-prospective-cloud-capture.yml > <temporary-before-file>
git show origin/ops/e2e-paper-cloud-launcher-v1:.github/workflows/e2e-paper-cloud-orchestration.yml > <temporary-before-file>
```

## Tag creation and verification

Create annotated tags locally at exact SHAs. Example pattern:

```bash
git tag -a archive/capture-hygiene-v3/forward-open-scaffold-dc5e84b5-tag \
  dc5e84b589eebe040119f48f9f69538d398a9d36 \
  -m "Capture Hygiene V3 archive: superseded forward Open scaffold"
```

Repeat for all four exact heads, then verify:

```bash
git rev-parse archive/capture-hygiene-v3/forward-open-scaffold-dc5e84b5-tag^{}
git rev-parse archive/capture-hygiene-v3/stockbit-v1-base-009be16e-tag^{}
git rev-parse archive/capture-hygiene-v3/stockbit-observable-smoke-17803978-tag^{}
git rev-parse archive/capture-hygiene-v3/market-index-eod-8c94f56b-tag^{}
```

Each dereferenced tag must equal its audited SHA.

## Destructive remote update

Prefer one `git push --atomic` transaction containing:

- the four permanent tag creations;
- deletion of the 10 merged/contained obsolete branches;
- deletion of the 4 unique superseded source branches;
- deletion of the 4 temporary archive branch refs.

Do **not** include protected refs or unrelated branches in the transaction.

If the remote does not support atomic push, stop and report that limitation before performing piecemeal destructive deletion. Do not silently downgrade safety.

## Post-apply verification

After a successful atomic push:

1. `git fetch origin --prune --tags`.
2. Prove all four permanent tags dereference to the exact audited SHAs.
3. Prove all 18 intended deleted branch refs are absent (10 merged/contained + 4 superseded sources + 4 temporary archive branches).
4. Prove protected refs are unchanged from preflight.
5. Re-read the three workflow files captured before mutation and verify their bytes are unchanged on their owning refs.
6. Verify Official Open remains pinned by commit SHA / deployment variable contract, Stockbit Stream remains default-branch based, and E2E launcher remains pinned to accepted `043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2` unless a separately reviewed deployment changed it.
7. Do not touch Windows scheduled tasks during this ref cleanup.
8. Record an exact result checkpoint with pre/post branch count, deleted refs, tag SHAs, main SHA, and confirmation that no runtime/data mutation occurred.

## Failure rule

Any unexpected SHA, unmerged dependency, protected-ref movement, non-atomic remote limitation, or workflow-byte difference is `BLOCKED_CAPTURE_HYGIENE_V3_<REASON>`. Stop without trying to rescue the cleanup by force-push or broad deletion.

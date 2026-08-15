# Repository Hygiene V1 — Batch 2 Post-Action Report

## Decision

`REPOSITORY_HYGIENE_V1_BATCH1_ACCEPTED_ARCHIVED_BRANCH_RETIREMENT_EXECUTED`

This report records the authorized second destructive batch from the accepted
repository-hygiene dry run. Only the 30 exact
`ARCHIVE_TAG_THEN_DELETE_BRANCH` candidates were deleted. Archive tags remain
the immutable provenance anchors.

Audit branch: `codex/repository-hygiene-v1`
Audit branch HEAD before this report commit: `076c515db74cbdcc254a2ffd4867918c99a6f900`
Source inventory: `docs/repository_hygiene/BRANCH_INVENTORY_V1.csv`
Action manifest: `docs/repository_hygiene/POST_ACTION_MANIFEST_V2.csv`

## Preconditions and PR handling

- Full `origin` fetch/prune completed before the final pre-delete gate.
- All 30 candidates were still present at their exact audited branch HEADs.
- All 30 archive tags existed remotely, were locally verified as annotated
  objects (`git cat-file -t` = `tag`), and peeled to the exact audited commit.
- No candidate had an active coordination status. Current `TEAM_STATUS` rows
  were `DONE`; no current-main handoff under `coordination/handoffs` referenced
  a candidate as unresolved.
- PR #20 was independently fetched before mutation:
  `data/financial-pit-v1@25eaa67a7f5446234db470756fe8b5c12cbb7696`, exactly
  matching its archive tag and audited branch HEAD.
- PR #20 was closed as stale/superseded archival lineage. Final state:
  `closed`, `merged=false`, `draft=true`, head unchanged.
- No other PR was modified.

## Branch action

| Check | Result |
|---|---:|
| Remote branch count immediately before Batch 2 | 160 |
| Target branches authorized | 30 |
| Target branches deleted | 30 |
| Target branches still present after prune | 0 |
| Remote branch count after Batch 2 | 130 |
| New unrelated branches since original 160-branch audit | 2 |

The two unrelated branches retained were:

- `review/idx-joint-setup-readiness-v1-1-domain-acceptance`
- `research/idx-joint-setup-readiness-state-v1-1-domain-remediation`

Therefore the exact current delta is `160 -> 130`: thirty authorized deletes
and two unrelated additions relative to the original audit snapshot. No KEEP,
ABANDONED_NO_DECISION, or NEEDS_MANUAL_REVIEW branch was included in the delete
command.

After the immediate post-action snapshot and before final handoff verification,
one additional unrelated branch appeared:

- `data/idx-lbre-market-anchor-reconciliation-v1`

The final remote inventory is therefore **131** branches. This later addition
was not part of Batch 2 and was not touched. The action-time count remains
`160 -> 130`; the final count is `131` solely because of this subsequent remote
addition.

## Archive-tag verification

- Archive tag rows verified: **30/30**.
- Remote archive tag ref lines: **60** (annotated tag object plus peeled
  `^{}` ref for each tag).
- Annotated object check: **30/30** `tag`.
- Expected vs observed peeled commit SHA: **30/30 exact**.
- Remote tag object SHA matched the local tag object SHA for all 30 tags.
- Tags changed or deleted: **0**.

The complete per-branch/per-tag SHA ledger is in
`POST_ACTION_MANIFEST_V2.csv`.

## Race/staleness accounting

Target staleness at the final pre-delete gate: **0**. The single delete push
contained exactly the 30 target branch refs and reported all 30 as deleted.

Relative to the original audit snapshot, two non-target branch heads had
advanced by the time of post-action verification; they were not touched by the
delete operation and remain present:

- `data/idx-lbre-monthly-free-float-history-v1` (`f6537c0...` ->
  `bf0648c9dd37ad4a25e2de42d6f4a18fd19f857d`), classified
  `NEEDS_MANUAL_REVIEW`;
- `research/idx-financial-pit-alpha-v1` (`a677cda5...` ->
  `1a9bf7267728d9beec2a975ac4b4e931d0be16d0`), classified `KEEP`.

This is external remote drift, not a target deletion race. The original audit
`main` also advanced to `b54d2165cd78b4c95d51707ff9a5b66bf3e1443b`; the audit
branch remained at `076c515...` until this report commit. These changes are
recorded rather than normalized away.

## Scope protection

- O2, runtime, models, data artifacts, scientific files, and main history were
  not edited by this batch.
- No KEEP, ABANDONED_NO_DECISION, or NEEDS_MANUAL_REVIEW branch was deleted.
- No PR other than #20 was modified.
- No tag was recreated, moved, or deleted.

## Validation

Read-only post-action checks passed for target absence, tag annotation, exact
peeled SHA, remote tag presence, and branch inventory reconciliation. The
repository-hygiene task does not require pytest; no source or test files were
changed. `git diff --check` is required after this documentation commit.

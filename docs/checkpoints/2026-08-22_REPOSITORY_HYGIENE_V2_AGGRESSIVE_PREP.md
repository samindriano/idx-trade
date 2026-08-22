# Repository Hygiene V2 — Aggressive Preparation Checkpoint

Date: 2026-08-22 Asia/Jakarta
Status: `AGGRESSIVE_HYGIENE_V2_PREPARED_DRY_RUN_REQUIRED_DESTRUCTIVE_APPLY_NOT_AUTHORIZED`

## Trigger

Fresh repository inventory on 2026-08-22 found 273 remote branches before creating this V2 preparation branch. Repository Hygiene V1 had classified only 138 branches at its older snapshot, so its conservative plan is stale and insufficient.

User direction: prune aggressively while preserving important scientific value. Failed or distant experiments may be removed as live branches if their conclusions are documented in detail.

## Actions already completed

- created `chore/repository-hygiene-v2-aggressive` from then-current `main` `0f5ae68ff113264513ed4c96e452cc2688e4de16`;
- added aggressive retention policy;
- added detailed experiment tombstone ledger;
- added exact retention/archive config with default-delete semantics;
- implemented fail-closed two-phase branch cleanup utility;
- closed obsolete historical PRs across early Stage3/4/4B/5, Open-backfill/data-foundation/sidecar work and Decision research;
- open PR inventory was reduced to only live Stockbit Stream PR #35 and adversarial audit PR #36;
- explicitly protected both Stockbit Stream PR head lineages in the retention allowlist.

No remote branch has been deleted by Hygiene V2 yet.
No archive tag has been created by Hygiene V2 yet.
No scientific data/runtime/model/outcome artifact has been modified.

## V2 retention philosophy

Live branches are reserved for:

1. current E2E/prospective/runtime dependencies;
2. current active data/research lanes with plausible future use;
3. a compact set of exact reusable scientific anchors.

Important historical exact-code anchors that do not need to remain branches become archive tags. The rest are tombstoned and deleted.

Target after cleanup: approximately 50–70 remote branches.

## Next required step

Run **plan mode only** from this exact preparation branch using:

`python scripts/repository_hygiene_v2.py plan --output <fresh_external_or_temp_path>`

The plan must be returned to ChatGPT with:

- exact branch/HEAD;
- `origin/main` SHA;
- remote branch count;
- KEEP count;
- ARCHIVE_TAG_THEN_DELETE count;
- TOMBSTONE_THEN_DELETE count;
- estimated live branch count;
- missing configured KEEP/archive entries;
- plan file SHA-256;
- complete KEEP list;
- complete archive list;
- any obviously suspicious deletion candidate family.

Plan mode is read-only except `git fetch --prune` and writing the local plan JSON. It must not create tags or delete branches.

## Destructive authorization boundary

`DESTRUCTIVE_BRANCH_CLEANUP_AUTHORIZED = false`

Do not run the `apply` subcommand until the exact plan is independently reviewed and ChatGPT supplies the exact plan SHA plus explicit authorization.

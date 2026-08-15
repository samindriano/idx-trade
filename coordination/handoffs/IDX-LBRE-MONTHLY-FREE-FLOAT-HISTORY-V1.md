# Handoff — LBRE Monthly Free-Float History V1

from: ChatGPT/LBRE-Monthly-History
to: Codex/LBRE-Monthly-History
branch: `data/idx-lbre-monthly-free-float-history-v1`
scientific parent: `data/idx-lbre-lineage-parser-remediation-v1@a42715f027fceb0c7cd24f68e65c9e91b7bfa049`
status: `PREPARED_CLAIM_REQUIRED_BEFORE_IMPLEMENTATION`

## Mandatory first action

Before changing code, reading the local external corpus for acquisition work, or making any provider/network call:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer lane owns monthly LBRE statutory free-float history;
3. claim on canonical main while preserving all concurrent changes:

`LBRE monthly free-float history V1 | ACTIVE | Codex/LBRE-Monthly-History | data/idx-lbre-monthly-free-float-history-v1 | official issuer LBRE position history 2024-04-30..2026-06-30; generalized exact parser + PIT correction replay; gaps explicit; no daily fill/features/models`

Do not proceed until the canonical claim is committed.

## Read first

- `AGENTS.md`
- `docs/checkpoints/2026-08-15_LBRE_MONTHLY_FREE_FLOAT_HISTORY_PREP.md`
- parent result `docs/checkpoints/2026-08-15_LBRE_LINEAGE_PARSER_REMEDIATION_RESULT.md`
- parent historical snapshot result `docs/checkpoints/2026-08-15_HISTORICAL_STATUTORY_FREE_FLOAT_SNAPSHOT_RESULT.md`
- `src/idx_trade/historical_statutory_free_float.py`
- `src/idx_trade/historical_statutory_free_float_io.py`
- `src/idx_trade/lbre_lineage_remediation.py`
- `scripts/run_lbre_lineage_parser_remediation.py`
- related tests.

## Parent roots to verify before reuse

Historical snapshot root:

`D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`

Manifest SHA-256:

`7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`

Remediation root:

`D:\Documents\Project\idx-lbre-lineage-parser-remediation-20260815-v1-final6`

Manifest SHA-256:

`cb2e929a8e7d5fc481c0eed6add4a6ba848c5a3374c65ea38e5fbe3fa5727244`

Verify hashes exactly. Do not mutate either parent root.

## Historical target

Position months only:

`2024-04-30` through `2026-06-30`, inclusive (27 target position months).

Publication search may extend after each position month and through the fixed cutoff `2026-08-15` because LBRE filings/corrections are published after period end.

Do not expand to 2021-2023 or position July 2026 in this V1.

## Implementation prerequisite — generalize, do not copy forensic ticker rules

The remediation runner's HILL/WINS/SKBM/PGUN/BAPA/BTPS branches are bounded forensic evidence, not production logic.

Implement a generalized monthly-history acquisition/replay path. It may reuse existing tested primitives but must not dispatch by hardcoded ticker identity.

General rules allowed:

- deterministic collapse of byte-identical duplicate transport references;
- same-announcement re-upload collapse only when announcement identity, ticker-position identity, and parsed economic values are exactly equivalent; preserve source aliases/hashes;
- explicit `KOREKSI`/`CORRECTION` marker classification;
- correction linkage only to a unique compatible prior active state or explicit official supersession reference;
- multiple genuine originals remain unresolved;
- current FF shares and current FF percentage must both be explicit official values;
- no percentage×shares arithmetic to repair missing fields;
- no narrative/fuzzy fallback when the authoritative current summary is ambiguous.

Add positive and adversarial tests for every generalized rule.

## Stage A — discovery inventory before bulk download

Use the accepted official IDX `ListedCompany/GetAnnouncement` metadata route and exact official StaticData attachment locator/transport.

Build a complete bounded discovery inventory first.

Requirements:

- query coverage and pagination evidence retained;
- raw metadata bytes/hash pinned;
- title/category matching documented;
- position date is not inferred from publication month alone;
- corrections/reuploads preserved in discovery population;
- all target-position candidates have stable official announcement identities.

Write a pre-download census by apparent publication month/year and discovered issuer count.

If pagination completeness or transport semantics change materially from the accepted parent, stop and document rather than silently switching source semantics.

## Stage B — acquisition

Create a new immutable external root, suggested:

`D:\Documents\Project\idx-lbre-monthly-free-float-history-20260815-v1`

Reuse June-2026 official bytes from the parent by exact hash/path identity.

For new files:

- official IDX bytes only;
- deterministic bounded retries;
- hash before parsing;
- no overwrite;
- exact URL + announcement + metadata provenance;
- final transport failures explicitly retained.

Do not put bulk PDFs in Git.

## Stage C — parse all target-position reports

Produce all candidate parse dispositions:

- exact;
- missing current percentage;
- missing current FF shares;
- invalid listed shares;
- malformed/non-integer number;
- FF shares > listed shares;
- identity/position unresolved;
- unsupported template;
- another evidence-backed failure category.

New template support is allowed only when current shares + current percentage are explicit and unambiguous.

The official percentage remains authoritative; arithmetic percentage is diagnostic only.

## Stage D — generalized revision replay

For every ticker-position key:

1. normalize deterministic transport aliases;
2. classify explicit correction markers;
3. preserve all economic revisions append-only;
4. replay by official publication timestamp;
5. link corrections only under deterministic evidence;
6. retain ambiguous multiple originals/correction chains unresolved.

Do not use latest-timestamp-wins as a generic original-selection rule.

Materialize:

- all admitted revision observations;
- current exact observations after replay;
- unresolved parser rows;
- unresolved lineage rows;
- alias/duplicate audit.

## Stage E — coverage and consistency audit

Per target position month report:

- announcements discovered;
- unique attachment identities;
- download successes/failures;
- parser exact/unresolved;
- original/correction counts;
- lineage admitted/excluded;
- current exact ticker count;
- unique ticker-position keys;
- ambiguity taxonomy;
- publication timestamp coverage.

Do not compute a false 'issuer coverage percentage' against an assumed 900-ish universe. Historical issuer universe is not certified for this lane.

Where available, compare 2025-12-31 issuer LBRE current values against the already accepted exact market-wide rows using existing `AGREE / CONFLICT / SINGLE_SOURCE` semantics. Preserve conflicts.

Also confirm that the new generalized path reproduces the accepted June-2026 post-remediation current state (`877` exact current observations) or explain every evidence-backed difference. A silent difference is a blocker.

## PIT rules

- report position date = economic state date;
- official IDX announcement timestamp = knowledge time;
- retrieval time is never historical knowledge time;
- corrections affect knowledge state only from their own publication timestamps;
- no backdating correction content into earlier knowledge states.

## No synthetic panel

Do not create ticker×month rows for issuers not evidenced in the discovery population.

No forward-fill, interpolation, carry-back, carry-forward, or `NO_OBSERVATION` assertion based only on absence from search results.

## Hard boundaries

No:

- holder/HSC/>=1% reconstruction;
- Ownership Change Event work;
- daily free-float state;
- effective/mobile supply;
- float turnover / FF market cap / Foreign Flow normalization;
- model or outcome access;
- O2 changes;
- Financial PIT/Corporate Action/TradingView/AKSes work;
- extension outside the 27 target position months.

## Required artifacts

External:

- raw metadata discovery captures;
- acquisition inventory;
- attachment hash inventory;
- parser audit;
- alias/duplicate audit;
- lineage/revision audit;
- all admitted observation table;
- current exact observation table;
- unresolved inventory;
- month-level census;
- 2025-12 cross-source reconciliation;
- final manifest.

Git:

- generalized monthly acquisition/parser/replay code and tests;
- `docs/checkpoints/2026-08-15_LBRE_MONTHLY_FREE_FLOAT_HISTORY_RESULT.md`;
- `coordination/handoffs/IDX-LBRE-MONTHLY-FREE-FLOAT-HISTORY-V1-RESULT.md`.

## Validation

Run focused historical/LBRE suites, full pytest, and `git diff --check`.

The known unrelated storage expectation failure may remain; do not modify storage.

## Completion verdict

Choose exactly one:

- `LBRE_MONTHLY_FF_HISTORY_READY_WITH_GAPS`
- `LBRE_MONTHLY_FF_HISTORY_PARTIAL_SOURCE_USEFUL`
- `LBRE_MONTHLY_FF_HISTORY_SOURCE_REMEDIATION_REQUIRED`

Update canonical TEAM_STATUS to `REVIEW`, commit/push, then stop for ChatGPT review. Do not automatically build a daily FF state or features.

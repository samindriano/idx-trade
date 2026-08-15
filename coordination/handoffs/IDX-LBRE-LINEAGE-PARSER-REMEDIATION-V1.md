# Handoff — LBRE Lineage / Parser Remediation V1

from: ChatGPT/LBRE-Remediation
to: Codex/LBRE-Remediation
branch: `data/idx-lbre-lineage-parser-remediation-v1`
scientific parent: `data/idx-historical-statutory-free-float-snapshot-v1@4762f4751cb4cc30d348704c7e19e65c47b7a329`
status: `PREPARED_CLAIM_REQUIRED_BEFORE_RUNTIME`

## Mandatory first action

Before changing parser/lineage logic, reading the external corpus for remediation, or making any provider/network request:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer lane owns LBRE parser/correction-lineage remediation;
3. claim this lane on canonical main, preserving every concurrent change:

`LBRE lineage/parser remediation V1 | ACTIVE | Codex/LBRE-Remediation | data/idx-lbre-lineage-parser-remediation-v1 | same immutable 2026-06-30 census only; classify/remediate 18 parser-unresolved + 93 lineage-excluded cases; no new month acquisition/features/models`

The ChatGPT GitHub connector created the branch and preparation docs, but did not have an append-safe primitive for the large shared status file. Do not proceed past coordination prep until the canonical claim is committed.

## Read first

- `AGENTS.md`
- `docs/checkpoints/2026-08-15_LBRE_LINEAGE_PARSER_REMEDIATION_PREP.md`
- parent result checkpoint:
  `docs/checkpoints/2026-08-15_HISTORICAL_STATUTORY_FREE_FLOAT_SNAPSHOT_RESULT.md`
- `src/idx_trade/historical_statutory_free_float.py`
- `src/idx_trade/historical_statutory_free_float_io.py`
- `tests/test_historical_statutory_free_float.py`
- `tests/test_historical_statutory_free_float_io.py`

## Immutable parent evidence

Root:

`D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`

Manifest SHA-256:

`7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`

Verify the exact parent manifest before analysis. If it mismatches, stop fail-closed.

Do not mutate the parent root.

## Frozen problem set

Parent census reported:

- 18 parser-unresolved rows;
- 93 exact rows excluded from lineage replay:
  - 35 `UNRESOLVED_NO_ORIGINAL`;
  - 29 `UNRESOLVED_MULTIPLE_ORIGINAL`;
  - 29 `UNRESOLVED_INVALID_CONTRACT_CHAIN`.

Build `problem_case_inventory.csv` from the parent evidence first. Every case must have stable identifiers, ticker if known, position date if known, announcement identity, attachment hash/path, current failure class, and final disposition.

Do not assume 18 + 93 are 111 unique issuer-period keys; report row-level and unique-case counts separately after inventorying the actual parent artifacts.

## Phase 1 — forensic classification, no code changes yet

For each parser-unresolved file, classify the exact cause, for example:

- PDF text/layout extraction issue;
- table/header variant;
- number formatting variant;
- explicit FF section absent;
- FF percentage only;
- FF shares only;
- ticker/position identity unresolved;
- malformed/corrupt/unsupported PDF;
- another evidence-backed category.

For each lineage exclusion, classify the exact reason from official metadata and bytes:

- missing earlier original in bounded corpus;
- correction mislabeled as original;
- duplicate transport copy;
- same-economic-content re-upload;
- multiple genuinely distinct originals;
- correction-of-correction chain;
- chronology conflict;
- identity mismatch;
- another evidence-backed category.

Preserve example cases for every taxonomy bucket.

## Phase 2 — parser remediation

Only implement parser changes where the official report visibly contains all fields required by the existing exact contract.

Rules:

- explicit FF share count and explicit FF percentage must be read, not reconstructed;
- no deriving shares from percentage × listed shares;
- no deriving percentage from shares unless only as diagnostic—the official percentage remains authoritative;
- no holder/HSC/>=1% arithmetic;
- template-specific parsing is preferred over fuzzy matching;
- every new parse path must have positive and adversarial regression fixtures/tests;
- previously accepted exact rows must remain semantically identical.

If a report lacks required exact fields, leave it unresolved.

## Phase 3 — lineage remediation

Use exact official publication metadata and document semantics.

Allowed deterministic repairs include:

- collapsing byte-identical duplicate attachment references after proving they represent the same publication/economic record;
- correcting a metadata normalization error that caused one explicit original to be missed;
- linking `ORIGINAL -> CORRECTION -> CORRECTION` only when publication chronology and explicit correction semantics establish every edge.

Disallowed:

- choosing one of multiple originals by latest timestamp without supersession evidence;
- inventing a synthetic original for a correction;
- ordering revisions by filename or retrieval time;
- treating numeric closeness as correction identity;
- silently dropping conflicting official publications.

## Phase 4 — exact same-corpus replay

Rerun the exact 2026-06-30 bounded corpus only.

Report before/after:

- parser exact rows;
- parser unresolved rows;
- original/correction counts;
- lineage admitted rows;
- current observations;
- each unresolved-lineage class;
- unique ticker-period keys;
- duplicate/ambiguous keys;
- any previously admitted row whose semantics changed (expected 0 unless a separately proven defect is documented).

Every recovered current observation must satisfy the existing historical FF contract and PIT chronology.

## Network policy

Default is **offline-only** using the already downloaded exact official corpus and captured metadata.

A provider call is not authorized merely to improve recovery. If a case appears resolvable only by an official announcement/attachment that is demonstrably missing from the parent bounded corpus, record it as `SOURCE_EVIDENCE_MISSING` and stop that case. Do not expand acquisition in this lane.

## External output

Create a new immutable root, e.g.:

`D:\Documents\Project\idx-lbre-lineage-parser-remediation-20260815-v1`

Required artifacts:

- parent manifest verification;
- problem-case inventory;
- parser taxonomy + examples;
- lineage taxonomy + examples;
- per-case disposition/evidence table;
- recovered exact observation table, if non-empty;
- post-remediation replay/current-state table;
- before/after audit summary;
- deterministic manifest + SHA-256.

No bulk raw files in Git.

## Tests

At minimum run:

```bash
python -m pytest tests/test_historical_statutory_free_float.py tests/test_historical_statutory_free_float_io.py -q
python -m pytest -q
git diff --check
```

Add focused remediation tests for every new parser or lineage rule.

Do not change the known unrelated storage expectation failure.

## Acceptance criteria

A scientifically acceptable result must have:

- 100% accounting of the frozen problem inventory;
- zero silent drops;
- zero invented values/revisions;
- zero non-official source promotion;
- zero PIT publication-time violations;
- zero accidental mutation of accepted parent observations;
- explicit residual ambiguity counts and reasons.

There is no minimum recovery-rate gate. Evidence integrity dominates coverage.

## Hard boundaries

Do NOT:

- acquire another month;
- launch full monthly history;
- modify quarterly market-wide anchors;
- perform holder-level FF reconstruction;
- use HSC or >=1% holder data to repair LBRE;
- forward-fill/interpolate;
- create ownership-change events;
- compute effective supply, float turnover, FF market cap, or Foreign Flow-normalized features;
- fit models/access outcomes;
- touch O2, Foreign Flow, Financial PIT, Corporate Action, TradingView, or AKSes lanes.

## Result documentation

Add:

- `docs/checkpoints/2026-08-15_LBRE_LINEAGE_PARSER_REMEDIATION_RESULT.md`
- `coordination/handoffs/IDX-LBRE-LINEAGE-PARSER-REMEDIATION-V1-RESULT.md`

Update canonical `TEAM_STATUS.md` to `REVIEW` at completion.

Return:

- final HEAD + clean/synced state;
- external root + manifest SHA;
- exact frozen problem inventory counts;
- parser taxonomy and recovered count;
- lineage taxonomy and recovered count;
- before/after 2026-06-30 exact/current counts;
- residual unresolved cases;
- test results;
- one verdict:
  - `LBRE_REMEDIATION_ACCEPTED_MONTHLY_HISTORY_READY`
  - `LBRE_REMEDIATION_ACCEPTED_WITH_RESIDUAL_AMBIGUITY`
  - `LBRE_REMEDIATION_BLOCKED_SOURCE_AMBIGUITY`

Stop for ChatGPT review. Do not automatically launch monthly history acquisition.

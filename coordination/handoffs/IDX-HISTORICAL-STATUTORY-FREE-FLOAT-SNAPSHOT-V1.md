# Handoff — Historical Statutory Free Float Snapshot V1

from: ChatGPT/Historical-Statutory-Free-Float  
to: Codex/Historical-Statutory-Free-Float  
branch: `data/idx-historical-statutory-free-float-snapshot-v1`  
scientific parent: `data/idx-statutory-free-float-reconstruction-v1@9eb73df879d44456adfc8d5f717e6c75be5d07a0`  
status: `CONTRACT_PREPARED_RUNTIME_SOURCE_CENSUS_REQUIRED`

## First coordination step — mandatory

Before tests that depend on local checkout and before any provider/network call:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer lane owns historical statutory free-float snapshot history;
3. claim this lane on canonical main without overwriting concurrent changes:

`Historical statutory free-float snapshot V1 | ACTIVE | Codex/Historical-Statutory-FF | data/idx-historical-statutory-free-float-snapshot-v1 | official reported snapshot history; quarterly market-wide anchors first; bounded monthly LBRE census; PIT corrections/cross-source reconciliation; no daily fill/features/models`

The ChatGPT connector prepared the feature branch but did not replace the large shared TEAM_STATUS file. The canonical claim must happen before live source work.

## Read first

- `AGENTS.md`
- `docs/checkpoints/2026-08-15_HISTORICAL_STATUTORY_FREE_FLOAT_SNAPSHOT_PREP.md`
- `docs/checkpoints/2026-08-15_HISTORICAL_STATUTORY_FREE_FLOAT_SNAPSHOT_CONTRACT_PREP.md`
- `src/idx_trade/historical_statutory_free_float.py`
- `src/idx_trade/historical_statutory_free_float_io.py`
- `tests/test_historical_statutory_free_float.py`
- `tests/test_historical_statutory_free_float_io.py`
- parent result:
  `data/idx-statutory-free-float-reconstruction-v1:docs/checkpoints/2026-08-15_STATUTORY_FREE_FLOAT_RECONSTRUCTION_RESULT.md`

## Run contract tests before network

```bash
python -m pytest tests/test_historical_statutory_free_float.py tests/test_historical_statutory_free_float_io.py -q
```

Fix only genuine defects in this new historical-snapshot contract. Do not modify unrelated storage behavior.

## Reuse parent external evidence

Parent root:

`D:\Documents\Project\idx-statutory-free-float-reconstruction-20260815-v1`

Parent manifest SHA-256:

`ff25cefed69af8cd221530a23f6fc31e85e0c510a21ef5bfb78526d618a45454`

It already contains exact official bytes for:

- `Peng-S-00006/BEI.PLP/02-2026` — position 2025-12-31 — 956 rows;
- `Peng-S-00011/BEI.PLP/04-2026` — position 2026-03-31 — 956 rows;
- 15 issuer LBRE records across DCII, WBSA, RLCO, BREN, BBCA, TLKM, MAYA, including 5 corrections.

Reuse only after verifying exact path/hash identity against the parent manifest. Do not redownload those bytes merely to create a new copy.

## New external root

Create for example:

`D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`

Preserve new official metadata captures, new official attachments, normalized CSV/JSON, reconciliation/census reports, query coverage, and final manifest/hashes outside Git.

## Stage A — official market-wide anchors

Goal: recover the actual official row-complete market-wide free-float status history available in the proven 2024–2026 era.

Use accepted IDX announcement metadata + exact StaticData `FullSavePath` transport. Search around these position dates as **targets only**:

- 2024-03-31
- 2024-06-30
- 2024-09-30
- 2024-12-31
- 2025-03-31
- 2025-06-30
- 2025-09-30
- 2025-12-31 — reuse parent
- 2026-03-31 — reuse parent
- 2026-06-30 if an official full-universe report exists by cutoff 2026-08-15.

Do not infer that every target exists.

For every candidate:

1. pin exact announcement metadata bytes/hash;
2. pin exact official attachment bytes/hash;
3. determine whether attachment is genuinely row-complete market-wide FF status versus sanction/suspension-only list;
4. extract explicit ticker, free-float shares, free-float pct, and total listed shares if present;
5. preserve publication timestamp separately from position date;
6. record row locator/key because many ticker rows share one attachment hash;
7. fail closed on duplicate/ambiguous ticker rows.

Materialize accepted observations using exact `HISTORICAL_FF_COLUMNS` order.

## Stage B — bounded monthly LBRE census

Do not bulk-download the full 2024–2026 monthly corpus yet.

Census one recent complete position month, preferably 2026-06-30 if metadata supports it. Discover the market-wide issuer LBRE announcement population for that position month and report:

- discovered issuer announcements;
- exact official attachment retrieval success count/rate;
- count with explicit FF shares + pct;
- original/correction counts;
- correction-lineage resolution rate;
- unique issuers;
- duplicate/ambiguous issuer-position identities;
- BAE/template families or material schema variations;
- publication timestamp coverage;
- approximate attachment volume / file count for a future full monthly acquisition.

A bounded census may retrieve the full selected month if discovery count is reasonable. Do not expand automatically to all 28 months.

Use the already recovered seven-ticker parent sample as adversarial cross-checks, not as the only census universe.

## Cross-source reconciliation

Where a market-wide anchor and issuer LBRE observation share the same ticker and `as_of_date`:

- run `replay_historical_free_float()` first so corrections are PIT-correct;
- run `reconcile_cross_source()`;
- retain `AGREE`, `CONFLICT`, or `SINGLE_SOURCE` explicitly;
- never choose a preferred value inside a `CONFLICT` in this lane.

Report conflict examples with both official source identities and numeric spreads.

## Census rules

Use `census_historical_free_float()` or an equivalent output based on exactly the same semantics.

Report only:

- observed position dates;
- issuer count per observed date;
- unique ticker count;
- source-family counts;
- corrections;
- cross-source status counts.

Do not manufacture missing monthly observations or assume an expected monthly issuer denominator unless an independently certified universe source is explicitly admitted.

## Important scientific interpretation

This lane handles **official reported statutory FF observations**. The parent `SOURCE_REMEDIATION_REQUIRED` verdict applies to independent rule/holder reconstruction and historical completeness; it does not invalidate an explicit official reported FF observation whose exact official bytes and publication timing are proven.

## Hard boundaries

Do NOT:

- attempt holder-level FF reconstruction;
- use `100% - sum(>=1%)`;
- subtract HSC concentration;
- infer free float from investor type/current Company Profile;
- create daily carry-forward/interpolation;
- create Ownership Change Event logic;
- calculate effective/mobile supply;
- build turnover/Foreign Flow/free-float/free-float-market-cap features;
- access labels/protected outcomes/models;
- touch O2, Financial PIT, Corporate Actions, TradingView, or Foreign Flow lanes.

## Validation before completion

Run:

```bash
python -m pytest tests/test_historical_statutory_free_float.py tests/test_historical_statutory_free_float_io.py -q
python -m pytest -q
git diff --check
```

If the known unrelated `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` failure remains, report exactly and do not modify storage.

## Required result documentation

Add:

- `docs/checkpoints/2026-08-15_HISTORICAL_STATUTORY_FREE_FLOAT_SNAPSHOT_RESULT.md`
- `coordination/handoffs/IDX-HISTORICAL-STATUTORY-FREE-FLOAT-SNAPSHOT-V1-RESULT.md`

Return:

- final branch HEAD + clean/synced state;
- external root + final manifest SHA-256;
- exact recovered market-wide anchor dates and row counts;
- gaps/unavailable targets;
- monthly LBRE census statistics;
- corrections and cross-source reconciliation counts;
- normalized CSV/JSON SHA-256;
- focused/full test results;
- one final verdict:
  - `HISTORICAL_STATUTORY_FF_SNAPSHOT_READY_QUARTERLY`
  - `HISTORICAL_STATUTORY_FF_SNAPSHOT_READY_WITH_GAPS`
  - `HISTORICAL_STATUTORY_FF_SOURCE_REMEDIATION_REQUIRED`

Stop for ChatGPT review after that. Do not automatically launch full monthly acquisition or feature integration.

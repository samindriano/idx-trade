# Handoff — Statutory Free Float Reconstruction V1

from: ChatGPT/Statutory-Free-Float
branch: `data/idx-statutory-free-float-reconstruction-v1`
status: `CONTRACT_PREPARED_OFFICIAL_SOURCE_AUDIT_REQUIRED`

## First coordination step

Before live/network work:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer lane owns statutory free-float reconstruction;
3. claim this lane on canonical main without overwriting concurrent changes:

`Statutory free-float reconstruction V1 | ACTIVE | Codex/Statutory-Free-Float | data/idx-statutory-free-float-reconstruction-v1 | bounded official-rule + BEI/LBRE source audit; official reported FF preferred; reconstruction only complete-or-bounded; no HSC/GT1 subtraction/features/models`

The ChatGPT connector could safely create the feature branch but could not
perform a conflict-safe append-only TEAM_STATUS edit without replacing the
large shared file, so the canonical claim must occur before the first provider
request.

## Read first

- `AGENTS.md`
- `docs/checkpoints/2026-08-15_STATUTORY_FREE_FLOAT_RECONSTRUCTION_PREP.md`
- `src/idx_trade/statutory_free_float.py`
- `tests/test_statutory_free_float.py`
- accepted direct endpoint checkpoint:
  `data/idx-direct-endpoint-audit-v1:docs/checkpoints/2026-08-13_IDX_ISSUED_HISTORY_FINANCIAL_REPORT_PROBE.md`
- accepted ownership/HSC source lineage and final HSC ledger for diagnostics only.

## Scientific rule

The primary target is **statutory free float**, not economically effective
supply.

Preferred evidence hierarchy:

1. explicit official reported free-float shares/pct from BEI monitoring or
   issuer LBRE/monthly registration report;
2. complete rule-aware reconstruction only if every relevant share is
   classified and unresolved shares are zero;
3. otherwise interval-only `BOUNDED_ONLY`;
4. otherwise `UNRESOLVED`.

Never calculate `100% - sum(>=1% holders)`.
Never classify a holder as non-free-float merely because it is >=1%, HSC,
corporate/institutional, local/foreign, or appears in Company Profile.

## Bounded source audit

### 1. Recover official rule bytes

Recover and hash official IDX bytes for:

- `Kep-00045/BEI/03-2026` / Regulation I-A 2026;
- `SE-00004/BEI/03-2026`;
- historical `Kep-00101/BEI/12-2021` / Regulation I-A 2021;
- any implementation circular materially affecting free-float classification,
  especially historical affiliate/approved-holder treatment.

Extract exact rule clauses needed to classify:

- ownership threshold;
- controller;
- controller affiliate;
- directors/commissioners;
- treasury shares;
- scripless/listed requirement;
- transfer-restriction exclusions under the applicable version;
- any holder category that can be specifically approved by IDX to count as
  free float despite a default exclusion/structure;
- effective dates and transition semantics.

Do not implement classification from secondary legal commentary when official
bytes can be obtained.

### 2. Recover market-wide official reported FF

Priority official locator targets:

- `Peng-S-00006/BEI.PLP/02-2026`
  - position: 2025-12-31
  - old rule regime
  - public mirror shows table fields including `% Saham Free Float` and
    `Jumlah Saham Free Float`.

- `Peng-S-00011/BEI.PLP/04-2026`
  - publication: 2026-04-30
  - position: 2026-03-31
  - revised 2026 rule regime
  - reported to cover 956 listed companies.

Use accepted official IDX announcement metadata + StaticData transport where
possible. Preserve exact metadata bytes, PDF/attachment bytes, publication
timestamp, announcement number and SHA-256.

Audit historical announcement metadata for analogous market-wide free-float
status reports back through at least 2021. Determine actual cadence; do not
assume monthly/quarterly/annual from isolated examples.

### 3. Recover issuer monthly registration reports

Adversarial set:

- DCII
- WBSA
- RLCO
- BREN
- BBCA
- one ordinary non-HSC ticker
- at least one issuer with an explicit corrected monthly registration report.

For each recover official IDX announcement + attachments for one or more recent
months, including 2026-06-30 where possible.

Inventory exact report fields and BAE/template differences. Specifically look
for:

- total shares / paid-up shares / listed shares;
- total scripless and scrip shares;
- explicit free-float shares;
- explicit free-float percentage;
- holders >=5%;
- controller and affiliate identification;
- directors/commissioners;
- treasury shares;
- transfer-restricted/blocked shares if reported;
- any explicit approved-as-free-float holder adjustment;
- report position date;
- issuer/BAE report date;
- IDX publication timestamp;
- correction references.

### 4. Reconstruction audit — diagnostics only

For each adversarial sample:

- treat the explicit official reported FF as the benchmark;
- attempt reconstruction only from evidence that is explicit in official
  bytes and valid under the correct rule version;
- put every relevant share into exactly one of:
  - confirmed eligible,
  - confirmed excluded,
  - unresolved;
- require bucket sum to equal total listed shares;
- if unresolved > 0, use `reconstruct_statutory_free_float()` and confirm it
  emits `BOUNDED_ONLY` with no point estimate;
- if unresolved == 0, compare exact reconstruction against official reported
  FF and record absolute share and percentage-point difference;
- any unexplained mismatch is a blocker. Do not reclassify unknown holders to
  force a match.

### 5. Supporting source boundaries

- `GetIssuedHistory`: share-count/event cross-check only; not standalone PIT
  shares-outstanding.
- current Company Profile: diagnostic current holder/controller evidence only.
- >=1% ownership: concentration/disclosure only.
- KSEI BalanceposEfek: aggregate ownership composition only.
- HSC: concentration state only.

Do not promote any supporting source into statutory FF merely to improve
coverage.

## External artifact root

Create for example:

`D:\Documents\Project\idx-statutory-free-float-reconstruction-20260815-v1`

Preserve:

- official rule PDFs/bytes and hashes;
- official announcement metadata captures;
- official BEI market-wide FF attachments;
- bounded issuer monthly registration attachments;
- schema inventory;
- normalized benchmark sample table;
- reconstruction audit table;
- historical-depth/cadence census;
- final manifest and SHA-256.

No bulk raw official data in Git.

## Validation

Run before and after audit:

`python -m pytest tests/test_statutory_free_float.py -q`
`python -m pytest -q`
`git diff --check`

Do not modify the known unrelated storage expectation failure if it remains.

## Acceptance questions

The bounded audit must answer:

1. Can the market-wide BEI status announcements be recovered as official bytes
   with row-complete free-float shares/pct?
2. What is their historical depth and real cadence?
3. Do issuer monthly LBRE attachments provide consistent explicit statutory FF
   across BAEs/templates?
4. Can publication knowledge time be defended?
5. Can adversarial holder-level reconstruction reproduce explicit official FF
   without hidden assumptions?
6. Which dates/tickers can be `OFFICIAL_REPORTED`, which can be
   `RECONSTRUCTED_VERIFIED`, and which must remain `BOUNDED_ONLY` or
   `UNRESOLVED`?
7. Is the resulting source history deep enough to be useful for historical
   model research, or only 2025/2026+ prospective conditioning?

## Hard boundaries

Do NOT:

- infer effective/mobile free float;
- subtract HSC concentration from 100%;
- subtract all >=1% holders;
- use current holder roles to backfill historical classifications;
- daily-forward-fill free float;
- build HHI/top-holder/supply-tightness features;
- join to Foreign Flow/volume/price;
- fit/score models;
- access labels/protected outcomes;
- modify Financial PIT, Corporate Action, O2, TradingView, or other active lanes.

## Final verdict vocabulary

Return one of:

- `STATUTORY_FREE_FLOAT_OFFICIAL_SOURCE_READY_FOR_HISTORY`
- `STATUTORY_FREE_FLOAT_PARTIAL_SOURCE_USEFUL_BOUNDED_ONLY`
- `STATUTORY_FREE_FLOAT_SOURCE_REMEDIATION_REQUIRED`

Also return final branch HEAD, test counts, artifact root, manifest SHA, exact
historical depth/cadence, source coverage, and adversarial reconciliation table.

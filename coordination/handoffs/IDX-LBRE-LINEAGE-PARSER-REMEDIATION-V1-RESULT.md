# Handoff — LBRE Lineage / Parser Remediation V1 Result

from: Codex/LBRE-Remediation  
to: ChatGPT/review  
task_id: IDX-LBRE-LINEAGE-PARSER-REMEDIATION-V1  
branch: `data/idx-lbre-lineage-parser-remediation-v1`  
status: `REVIEW`

## Source and lineage

- Scientific parent: `data/idx-historical-statutory-free-float-snapshot-v1`
  @ `4762f4751cb4cc30d348704c7e19e65c47b7a329`.
- Parent external root:
  `D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`.
- Parent manifest SHA-256:
  `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`.
- Frozen corpus: immutable LBRE position `2026-06-30` only.

## Result

Verdict: `LBRE_REMEDIATION_ACCEPTED_WITH_RESIDUAL_AMBIGUITY`.

The exact evidence-backed repairs are accepted for review. Monthly history is
not started because 17 parser cases and 87 lineage rows remain excluded or
ambiguous.

## Counts

- Problem inventory: `111` row-level cases, `107` unique evidence keys.
- Parser: `1,050 exact / 18 unresolved` before; `1,051 exact / 17 unresolved`
  after; `1` recovery.
- Lineage: `957 admitted / 93 excluded / 871 current` before;
  `963 admitted / 87 excluded / 877 current` after; `6` recovered lineage
  rows.
- Admitted lineage revisions: `877 ORIGINAL / 80 CORRECTION` before;
  `882 ORIGINAL / 81 CORRECTION` after.
- Full replay observations: `964` (`883 ORIGINAL / 81 CORRECTION`), including
  the recovered BTPS parser row.

## Recovery rules

- BTPS: exact labelled current two-column summary only; narrative text is not
  used as a value source.
- HILL/WINS/SKBM: byte-identical transport duplicates collapsed.
- PGUN: same announcement and same economic content re-upload collapsed.
- BAPA: explicit `KOREKSI` marker corrected the revision kind and linked to the
  unique earlier original.

Residual ambiguity:

- parser: 13 missing current percentage, 1 malformed share number, 1 invalid
  listed-share field, 1 invalid free-float contract, 1 missing identity/fields;
- lineage: 35 missing original evidence, 29 invalid original-required chains,
  19 genuinely multiple-original cases.

No synthetic original, holder/HSC/>=1% arithmetic, forward-fill, or ambiguous
original selection was used.

## External artifacts

- Root:
  `D:\Documents\Project\idx-lbre-lineage-parser-remediation-20260815-v1-final6`
- Manifest SHA-256:
  `cb2e929a8e7d5fc481c0eed6add4a6ba848c5a3374c65ea38e5fbe3fa5727244`
- Required files include parent verification, problem inventory, parser and
  lineage taxonomies, recovered exact observations, replay/current table, and
  before/after summary.

## Validation

- Focused: `19 passed`.
- Full: `67 passed, 1 failed`; known unrelated storage expectation failure in
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  (expects one conflict, current contract surfaces independent raw and vendor
  close conflicts). No storage change was made.
- `git diff --check`: PASS.

## Boundaries respected

No provider calls, new month acquisition, monthly history expansion, FF
arithmetic, effective-supply features, Foreign Flow integration, models,
outcomes, O2, or unrelated lanes were touched.

## Next decision

Independent review should decide whether the residual ambiguity is acceptable
for a separate monthly-history acquisition contract. This task does not start
that work automatically.

head_commit: `6b8074a`

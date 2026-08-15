# Handoff

from: Codex/Historical-Statutory-Free-Float
to: ChatGPT reviewer / MAIN
task_id: IDX-HISTORICAL-STATUTORY-FREE-FLOAT-SNAPSHOT-V1
model_used: Codex Luna xhigh
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `6d5b7f28b4f2e0adf10fc47e63412b67896f5e27`
branch: `data/idx-historical-statutory-free-float-snapshot-v1`
head_commit: pending documentation commit

## Scope

Bounded official reported statutory free-float snapshot audit. Reused the two
hash-pinned parent market-wide reports, recovered a bounded 2026-06-30 issuer
LBRE population from existing official announcement captures, preserved exact
publication timestamps/correction lineage/source hashes, and reconciled rows
where both source families covered the same position.

No full monthly acquisition, daily fill, interpolation, holder/HSC
reconstruction, effective supply, Foreign Flow, feature, model, outcome, or
forward-runtime work was performed.

## Findings

- External root:
  `D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`
- External manifest SHA-256:
  `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`
- Reused parent manifest SHA-256:
  `ff25cefed69af8cd221530a23f6fc31e85e0c510a21ef5bfb78526d618a45454`
- Market-wide exact observations: 923 at position 2025-12-31.
- Market-wide 2026-03-31 report: percentage-only for this contract; no exact
  free-float share observations admitted.
- No complete 2024 quarterly, 2025 Q1–Q3, or 2026-06-30 market-wide anchor was
  proven by the bounded official search.
- LBRE discovery: 1,068 announcements, 1,064 unique main PDFs, 1,064/1,064
  successful downloads, 1,050 exact parsed rows, 18 parser-unresolved rows.
- LBRE exact 2026-06-30 input: 1,015 rows; 915 originals and 100 corrections;
  871 current observations after fail-closed lineage replay.
- Unified admitted observation rows: 1,882.
- Cross-source reconciliation: `AGREE=1`, `CONFLICT=1`, `SINGLE_SOURCE=1,798`.
- Verdict: `HISTORICAL_STATUTORY_FF_SNAPSHOT_READY_WITH_GAPS`.

## Decisions made

Exact official reported values only. Publication timestamps remain tied to the
official announcement/filing evidence; observed retrieval time is not a
retroactive knowledge time. Corrections remain independently represented and
are usable only from their own proven publication timestamp. Ambiguous,
percentage-only, invalid-contract, incomplete-lineage, or missing-linkage rows
remain outside the exact set.

## Validation run

- Focused: `python -m pytest tests/test_historical_statutory_free_float.py tests/test_historical_statutory_free_float_io.py -q` — 14 passed.
- Full: `python -m pytest --tb=short` — 61 passed, 1 failed, no warnings reported.
- Unrelated failure:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expects one conflict but receives the two independent `raw_close` and
  `vendor_adj_close` conflicts. No storage change was made.
- `git diff --check`: passed before the documentation commit.

## Blocking risks / next decision

Quarterly market-wide history remains incomplete. The next task, if approved,
should target missing official quarterly anchors or explicitly accept the
bounded single-anchor + LBRE coverage as a sparse snapshot source. It must not
infer statutory free float from holders, HSC, or arithmetic complements.

## Recommended next action

Independent ChatGPT review of the external manifest, the 923 exact market-wide
rows, the 871 current 2026-06-30 LBRE observations, and the AGREE/CONFLICT/
SINGLE_SOURCE reconciliation before any broader acquisition is authorized.

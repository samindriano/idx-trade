# Handoff — LBRE Monthly Free-Float History V1 Result

from: Codex/LBRE-Monthly-History
to: ChatGPT/review
task_id: IDX-LBRE-MONTHLY-FREE-FLOAT-HISTORY-V1
model_used: gpt-5.6-luna
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `f6537c09b5121cc8b185df4fd9d672e305a879d1`
branch: `data/idx-lbre-monthly-free-float-history-v1`
status: `REVIEW`
head_commit: `PENDING_COMMIT`

## Scope

Generalized official IDX issuer LBRE acquisition, explicit current
free-float parsing, append-only correction replay, and offline monthly census
for position dates 2024-04-30 through 2026-06-30 inclusive. The accepted June
parent corpus was reused by exact hash. No synthetic ticker-month grid,
forward-fill, interpolation, holder/HSC/>=1% reconstruction, effective
supply, features, models, or outcomes were used.

## Result

Final verdict: `LBRE_MONTHLY_FF_HISTORY_PARTIAL_SOURCE_USEFUL`.

Discovery was pagination-complete: 27,724 reported records, 28 pages, and
30,405 main attachments from 954 tickers. Acquisition produced 1,068 exact
parent reuses, 29,335 new downloads, and 2 bounded HTTP 404 failures.

Parsing produced 28,254 exact rows and 2,151 audit rows. Replay produced
25,262 canonical rows, 2,992 aliases, 24,394 admitted append-only
observations, 23,373 current observations, and 868 fail-closed lineage
unresolved cases. Full per-month acquisition/parser/lineage/current counts,
residual taxonomies, and June-2026 reconciliation are recorded in:

`docs/checkpoints/2026-08-16_LBRE_MONTHLY_FREE_FLOAT_HISTORY_RESULT.md`

June-2026 current is 870 versus the accepted 877 parent. The eight old-only
tickers are explained by multiple-original ambiguity, malformed/non-comparable
two-column evidence, or correction-without-original; INAF is a newly
discoverable exact source row. The generalized pipeline did not promote any
of the eight ambiguous cases.

2025-12 cross-source reconciliation: 260 AGREE, 625 CONFLICT, 38
SINGLE_SOURCE; no conflict was selected or overwritten.

## External artifacts

- Root:
  `D:\Documents\Project\idx-lbre-monthly-free-float-history-20260815-v1`
- Manifest SHA-256:
  `e134809a1f1b745daf2f21c33ab7db78c38d1d5d520f5320564359d5b865bd86`
- Manifest file count: `58,671`
- Parent snapshot manifest:
  `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`
- Parent remediation manifest:
  `cb2e929a8e7d5fc481c0eed6add4a6ba848c5a3374c65ea38e5fbe3fa5727244`

## Validation

- Focused LBRE/statutory tests: `21 passed`.
- Full pytest: `69 collected; 68 passed, 1 failed`.
- Failure is unrelated pre-existing storage expectation:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.
  No storage change was made.
- `git diff --check`: PASS.

## Recommended next action

ChatGPT independent review should decide whether this explicit partial source
is sufficient for a separate monthly-state contract. Do not start daily FF
state or feature integration automatically.

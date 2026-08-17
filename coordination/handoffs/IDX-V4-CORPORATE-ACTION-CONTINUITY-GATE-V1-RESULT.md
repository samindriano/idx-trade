# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-V4-CORPORATE-ACTION-CONTINUITY-GATE-V1
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: b536c832730bd0c5e2dd6952b44cf9b11b4573f9
branch: data/idx-v4-corporate-action-continuity-gate-v1
status: BLOCKED

## Scope

Outcome-blind final V4 `corporate_action_continuity_certified` gate audit over
the exact 739-ticker decision universe and frozen 600 validation dates. No
target, rank, model, performance, provider, protected outcome, or fresh-forward
access.

## Result

- Frozen dates: 600 (6 × 100), frozen decision rows: 172,395.
- Decision ticker universe: 739; universe SHA-256
  `700037b38a7202e4c8a58b1068a885f903a568493f379b7fcb3afa88cc620bbe`.
- Event evidence rows: 26.
- Mechanical families observed: stock split 7, stock dividend 3, bonus 1,
  rights/HMETD 10, mandatory conversion 4, capital restructuring 1.
- Reverse split and merger evidence rows: 0; absence is not treated as no
  event.
- Continuity ledger: 344,790 rows; 344,740 coverage-unresolved and 50
  effective-date-unresolved.
- H5/H10/consensus continuity gate: 0/600 dates at ≥90%; final verdict
  `BLOCKED`.

## Why blocked

The reused official CA root is bounded candidate/provenance evidence. It does
not prove a market-wide no-event condition, and its source-specific dates do
not establish a canonical effective date. IDX `TanggalPencatatan` is not used
as a generic effective date; KSEI cum/record/distribution dates remain
unresolved for market-effective price-basis use. Missing evidence therefore
fails closed as `PRICE_CONTINUITY_UNRESOLVED_COVERAGE`.

## Artifacts

External root:
`D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3`

- full ledger SHA-256 `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`;
- event evidence SHA-256 `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`;
- per-date SHA-256 `4f246f6f5773e978f177ea786bb8cce8d8e860ce5240818aa0287730ef35f4f8`;
- manifest SHA-256 `4dd75efc2542082d535b11131b59fcaf5f422d6cc0b567715435d65f6d026bca`.

Small summaries and evidence CSVs are promoted under
`docs/artifacts/ranking_v4_ca_continuity_gate_v1/`; the expanded ledger stays
external.

## Validation

Focused continuity tests: `3 passed`.
Full pytest: `85 passed, 1 failed / 86 collected`, only the unrelated existing
storage conflict-count expectation failed. `py_compile` and `git diff --check`
passed.

## Decision

Keep V4 historical target/model execution blocked. Do not rescue/tune, change
the target/evaluator/preregistration, or start a new CA acquisition without a
separately authorized source/effective-date contract.

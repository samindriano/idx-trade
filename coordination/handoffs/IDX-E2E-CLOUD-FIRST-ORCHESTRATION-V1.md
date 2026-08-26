# Handoff

from: Codex
to: MAIN / ChatGPT review
task_id: IDX-E2E-CLOUD-FIRST-ORCHESTRATION-V1
model_used: GPT-5
reasoning_level: high
source_repository: `samindriano/idx-trade`
source_commit: `8a96a3d9caebfbd2c0235234e9394afc04693efa`
branch: `integration/e2e-cloud-first-orchestration-v1`
head_commit: `d49ad9498df43b8a0f424dce4749198252369fa6`
scope: cloud-first E2E Paper durability/orchestration adapter and synthetic tests only

## Files changed

- `.github/workflows/e2e-paper-cloud-orchestration.yml`
- `src/idx_trade/e2e_paper_cloud_runtime_v1.py`
- `scripts/run_e2e_paper_cloud_v1.py`
- `tests/test_e2e_paper_cloud_runtime_v1.py`
- `docs/checkpoints/2026-08-26_E2E_CLOUD_FIRST_ORCHESTRATION_V1.md`

## Findings

- Existing E2E controller/PaperState and forward monitoring are local-path,
  SQLite, and subprocess based; the original main tree does not contain that
  implementation.
- Official Open and Stockbit already have cloud evidence workflows, but
  Official Open's existing commit replay does not verify child artifacts and
  its legacy store write is not a distributed create-only primitive.
- A direct full cloud replacement cannot be honestly claimed without a pinned
  input bundle, provider checkout, stable runtime rehydration, and a thin
  default-branch launcher.
- Cloud dispatch rejects an explicit non-current session date and operational
  prerequisites are checked before the existing EOD engine can make a provider
  call.
- Cloud stage replay verifies result/snapshot children, stage guards, and the
  current schedule/input identity before returning an existing commit.

## Decisions

- Reuse the existing E2E engines; add only a cloud durability/control adapter.
- Use private R2 with a separate `e2e-paper-v1` prefix and existing
  `official-open-v1` as an input source; no second PaperState database or
  capture hierarchy is introduced.
- Keep observed calendar and planned schedule distinct and hash-bound.
- Commit stage state only after the complete runtime snapshot and result can be
  read and verified. Expected wait states do not create a terminal commit.
- Preserve outcome-blind and no-retroactive-execution guards.
- Require all four clean model children and the fit log as explicit manifest
  roles; a model manifest alone is not a runnable model bundle.

## Blocking risks

- Cloud input artifacts are not yet provisioned or live-verified.
- The current default branch needs a separate thin launcher workflow pinned to
  the implementation SHA; this branch cannot make scheduled Actions run by
  itself.
- A live first-session proof is still required before Windows/manual operation
  can be retired.

## Validation run

- `python -m py_compile src/idx_trade/e2e_paper_cloud_runtime_v1.py scripts/run_e2e_paper_cloud_v1.py`: PASS
- `python -m pytest -q tests/test_e2e_paper_cloud_runtime_v1.py`: 13 passed (fresh basetemp)
- Relevant E2E/Official Open regression group: PASS (fresh basetemp)
- `python -m pytest -q`: PASS, 100% completed, 3 existing FutureWarnings
- `git diff --check`: PASS
- No provider/network calls, model fit/rescore, or protected outcome access.

## Recommended next action

Review this adapter and then create a separate default-branch thin launcher
commit pinned to the accepted implementation SHA. Provision and attest the
input manifest outside Git before attempting one controlled cloud session.
Do not retire Windows tasks or declare laptop-free operation until that proof
passes.

# Handoff: Cash Dividend + E2E Baseline Paper V1 Adversarial Remediation

from: Codex local implementation
to: ChatGPT / MAIN independent review
task_id: IDX-CASH-DIVIDEND-E2E-ADVERSARIAL-20260823
model_used: GPT-5 Codex
reasoning_level: high
source_repository: `samindriano/idx-trade`
branch: `integration/idx-e2e-baseline-paper-v1`
head_commit: ce91d60a8b9b5bdbedad15e7a4f0254d69b4d2f2
scope: Remediate and adversarially validate the frozen cash-dividend and E2E
paper orchestration path without provider, outcome, model, or scheduler access.

## Files changed in this continuation

Implementation:

- `src/idx_trade/e2e_paper_orchestration_v1.py`
- `src/idx_trade/forward_dividend_execution_v1_1.py`
- `src/idx_trade/v4_x1_execution_v1_verify.py`
- `src/idx_trade/e2e_replay_boundary_v1.py`
- `scripts/run_e2e_paper_deterministic_replay_v1.py`
- `scripts/run_e2e_paper_deterministic_oracle_v1.py`
- `scripts/run_e2e_paper_production_replay_v1.py`
- `scripts/run_e2e_paper_cold_restart_replay_v1.py`

Tests:

- `tests/test_e2e_paper_orchestration_v1.py`
- `tests/test_forward_dividend_orchestration_v1.py`
- `tests/test_v4_x1_execution_v1_verify.py`
- `tests/test_e2e_replay_boundary_v1.py`

Documentation:

- `docs/checkpoints/2026-08-23_CASH_DIVIDEND_E2E_ADVERSARIAL_RESULT.md`
- this handoff
- the obsolete branch-local `coordination/TEAM_STATUS.md` section was
  removed; canonical TEAM_STATUS remains MAIN-owned and unchanged.

## Findings resolved

The prior A1–A9/B1–B9 remediation remains the parent of this continuation.
This continuation specifically closes the red-team harness gaps for explicit
economic oracles, a real child-process restart, POST_EOD/PREOPEN phase
separation, no-delta refresh, new-event extension, previous execution-parent
hashing, weekend/duplicate calendar rejection, and evidence-backed replay
boundary reporting. A same-announcement blocker recovery regression and a
deleted previous-execution parent regression were added.

## Fresh artifacts

- deterministic core: `0ea50f1bf46ee6e8b2fa38bc3fb87c4aa466d059062280458fa7caf2f71da0f2`
- deterministic economic oracle:
  `b76da401d1afbc1e6cf91771adafa38ac3cd014699954cb1096cdf29a94368b3`
- production artifact replay:
  `436c4405ea18e9e0cf3038e9f0b606b64064119267adae464ff2968772172166`
- cold restart replay:
  `c4684a607a73f61ed5275a167fe03aa260a550a9ed0ab783ef75bf42f0d5e73d`

Static replay-boundary audit hashes:

- deterministic core: `e0f44ad1461455d6d6c702457aecce1b097941d14ba0a8df84300f0b426aab01`
- deterministic economic oracle: `8776bcae2931349c223b5cad603781bda0d7f7ef0c5a565a5903144f871aa5fe`
- production/cold replay: `52722d7b835a2a1b08310a6a46d857abd8d0dd6a36a69127a7b1068126528a00`

All are external temporary roots and remain diagnostic/review artifacts; no
large runtime data or model binary is promoted to Git.

## Validation

- focused suite: **126 passed**;
- full suite: **662 passed**;
- py_compile: **PASS**;
- git diff --check: **PASS**;
- no provider/outcome/scheduler access.

Cold restart additionally reran completed execution session `2026-08-25` in a
third child process. It returned `ALREADY_COMPLETE` and proved execution,
runtime snapshot, and runtime-state hashes were unchanged.

## Decisions / remaining risks

- Frozen scientific/model/execution policies were not changed.
- No new provider or CA acquisition was attempted.
- The deterministic oracle intentionally uses token-gated synthetic objects to
  test pure economic functions; the production replay separately exercises
  real artifact verifiers and orchestration boundaries.
- Replay boundary evidence is produced by an AST import/call/marker audit of
  the hash-pinned replay sources. It is an explicit static boundary proof, not
  a claim of runtime telemetry.
- Production expected fills are independently calculated from frozen
  capacity, lot, price, fee, and cash rules; T06 independently resolves to
  4,900 shares and is never read from actual execution output.
- Production replay now compares exact per-session fill vectors, fees, cash,
  positions, receivables, settlements, turnover, stamp, pending transitions,
  CA delta, registry count, and receivable NAV delta. The deterministic oracle
  also checks both BUY and SELL fee/slippage paths and exact below/above
  threshold stamp behavior.
- Independent review is still required before any operational continuation.

recommended_next_action: independent ChatGPT review of the final diff,
fresh replay hashes, and the distinction between deterministic economic
oracle and production artifact replay. Keep lane at `REVIEW`.

# Handoff

from: Codex
to: MAIN / ChatGPT review
task_id: IDX-HISTORICAL-E2E-REPLAY-DATA-READINESS-V1
model_used: GPT-5 Codex
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: d49b1540d4e6b29deddc0f47ca0cf7cacc9e3b75
branch: research/idx-historical-e2e-replay-data-readiness-v1
head_commit: branch HEAD produced by the commit containing this handoff

## Scope

Outcome-blind data-readiness audit for the frozen Decision V2 600-session
trajectory, without targets, labels, realized outcomes, performance, model
fit/score, or provider/network access.

## Files changed

- `src/idx_trade/historical_e2e_replay_readiness_v1.py`
- `scripts/run_historical_e2e_replay_data_readiness_v1.py`
- `tests/test_historical_e2e_replay_readiness_v1.py`
- `docs/checkpoints/2026-08-23_HISTORICAL_E2E_REPLAY_DATA_READINESS_AUDIT_V1.md`
- this handoff

## External evidence

Audit root:
`D:\Documents\Project\idx-historical-e2e-replay-readiness-20260823-v6`

Manifest SHA:
`86304dac2226f40e58f18ea302f709106b67609165b4bb488bda4c5d7b4564e7`

Decision V2 structural manifest SHA:
`a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`

Clean panel SHA:
`25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`

## Findings

- 600 structural sessions, 2,584 intents, 5,693 exposure rows, 347 unique
  tickers.
- No consolidated historical sizing/execution artifact exists; the external
  Decision V2 structural artifact is explicitly `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`.
- Current Close/RMV are complete for exposure rows, but execution-grade Open
  is only 351 / 1,297 buy intents (27.0625%).
- Holding-input readiness is 1,350 / 5,693 (23.7133%).
- CA continuity is resolved for 4,471 / 5,693, with 1,222 unresolved under a
  fail-closed absence-does-not-prove-no-event policy.
- Dividend evidence is a bounded 7-event corpus only; 2 holding spells overlap
  bounded certified events and 1,295 remain without market-wide no-event proof.
- No full-economic strict contiguous segment is available.

## Decisions

Final verdict: `HISTORICAL_E2E_REPLAY_BLOCKED_BY_DATA`.

The artifact is diagnostic evidence only. It does not authorize a historical
performance replay, backfill, model run, or outcome access.

## Validation

- Focused audit tests: 5 passed.
- Full pytest: passed with isolated `--basetemp`; 3 pre-existing pandas
  FutureWarnings.
- `py_compile`: passed for module and runner.
- `git diff --check`: passed.

## Recommended next action

Keep this branch isolated and obtain independent acceptance for any future
600-session execution-state, Open, CA, or dividend evidence bundle before
attempting a replay. Do not edit `coordination/TEAM_STATUS.md` from this
branch; MAIN owns that file.

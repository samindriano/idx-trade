# Handoff

from: Codex
to: MAIN / ChatGPT review
task_id: IDX-HISTORICAL-E2E-REPLAY-V1-SCOPE-REMEDIATION-V2
model_used: GPT-5 Codex
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: `9c505366fa7704ec58ca976b32d9994c92d63ebb`
branch: `research/idx-historical-e2e-replay-v1`
head_commit: commit containing this handoff

## Scope

Outcome-blind hardening and fresh recomputation of the historical E2E scope.
The fixed 6x100 assumption was removed, but a non-zero start is deliberately
rejected until the runner has a reviewed predecessor-state anchor. No replay
or performance calculation was run because the strict scope is empty.

## Result

Verdict: `TRUE_HISTORICAL_E2E_REPLAY_SCOPE_BLOCKED_BY_CA_DIVIDEND_DATA`

Fresh scope output:
`D:\Documents\Project\idx-historical-e2e-scope-recompute-20260824-v9\REPLAY_SCOPE.json`

- file SHA-256:
  `cb765a5f1675ea35c2a4d075302c64fd6ac09d413ba8edb4a8198079ed203ae0`
- payload SHA-256:
  `f75cf7302f4bd27927e36e296634c7ae9adfcd32849ed8fc78555a9e27dc6fd7`
- status: `STRICT_SCOPE_EMPTY_BLOCKED`
- candidate range: 600 sessions
- strict range: 0 sessions
- blockers: `NO_CONTIGUOUS_EXPOSURE_COMPLETE_RANGE`,
  `DIVIDEND_EXPOSURE_WINDOW_PROOF_INCOMPLETE`

## Exact support diagnostics

- Open session manifests: 600/600 certified;
- BUY required/evidence/positive/non-positive/missing:
  `1297 / 1297 / 905 / 392 / 0`;
- SELL required/evidence/positive/non-positive/missing:
  `1287 / 1287 / 891 / 396 / 0`;
- BUY-ready sessions: 600/600;
- SELL-ready sessions: 600/600;
- CA exposure rows/resolved rows/fully-ready sessions:
  `5693 / 4471 / 40`;
- dividend exposure rows/ready rows/fully-ready sessions:
  `5693 / 11 / 0`.

Non-positive certified Open rows remain pending/unavailable under the frozen
Execution V1 semantics. They are not converted to positive prices or silently
treated as missing evidence.

## Pinned provenance

- readiness manifest:
  `86304dac2226f40e58f18ea302f709106b67609165b4bb488bda4c5d7b4564e7`
- readiness summary:
  `31aea94cf6cea52b1a2dcea25676f944bd13f06731b745f0179044f2aca9a040`
- exposure universe:
  `110d3f7543c33e90a7d2cea1352f6360e0385fd5399c4b61409ee3acba56d030`
- CA gap:
  `8172ef21fde01545a8d176ed1d2b40703663675c9577bc34791b820ab50e973b`
- dividend gap:
  `625c3dfe6986bd9f9309a9a2fad4cb0f8398dfb1edb770655784eac4187c2322`
- Open acquisition manifest:
  `dc74485c6d4ade01e125b08871105c8daea9c64f9daa2af6cc00d26592a8fcbf`
- CA manifest / ledger:
  `c635ee354c923eebdb586bc4d82a6693d230e1a347df50879dda4c1f5f56bff4` /
  `0c48aa4d12a66241378e1b95e2f51615b5ca3469a4c63692c5d9e7b8818a337f`
- dividend result:
  `454213df35c3ffd741cc137c24d502f1fc45cd46e229c1c553852b2418e07aac`
- calendar:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

## Files changed

Executable/test hardening:

- `src/idx_trade/v4_x1_execution_v1_verify.py`
- `src/idx_trade/historical_e2e_scope_validator_v1.py`
- `src/idx_trade/historical_e2e_replay_runner_v1.py`
- `src/idx_trade/historical_e2e_replay_v1.py`
- `scripts/freeze_historical_e2e_scope_v1.py`
- corresponding historical E2E and official-Open verifier tests.

Documentation:

- this handoff;
- `docs/checkpoints/2026-08-24_HISTORICAL_E2E_SCOPE_REMEDIATION_V2.md`.

## Validation

- focused tests: 58 passed;
- full pytest: 745 passed, 0 failed, 3 existing pandas warnings;
- `py_compile`: PASS;
- `git diff --check`: PASS.

## Boundaries

No labels, protected outcomes, scores, returns, NAV, model fit/score,
Monte Carlo, scheduler, counter, operational runtime, or provider call was
used. `coordination/TEAM_STATUS.md` was intentionally not edited because
MAIN owns that file.

## Recommended next action

Stop for independent review. Do not run replay or Monte Carlo. Continue only
with a separately reviewed CA/dividend/tradability evidence lane, or with a
new predecessor-state anchor design if a non-zero subrange is required.

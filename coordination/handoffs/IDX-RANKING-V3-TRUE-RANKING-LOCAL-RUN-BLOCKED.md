# Handoff - IDX Ranking V3-E True-Ranking Local Run Blocked

from: Codex
to: ChatGPT / research reviewer
task_id: IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `8f58b4884c6f4c7d45766737935c8fd1a9568e58`
branch: `research/idx-ranking-v2-spec-v1`
head_commit: `8f58b4884c6f4c7d45766737935c8fd1a9568e58`
scope: Frozen V3-E dependency/preflight gate only; no outcome run.

## Files changed

- `docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_BLOCKED_DEPENDENCY.md`
- `coordination/handoffs/IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN-BLOCKED.md`
- `docs/CURRENT_STATUS.md`
- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`

## Findings

- Branch was fetched and fast-forwarded to `8f58b4884c6f4c7d45766737935c8fd1a9568e58`.
- Working tree was clean and synchronized.
- Required XGBoost is exactly `3.2.1`; local import was `3.1.3`.
- Exact installation was attempted and failed because neither the configured
  package index nor public PyPI has an `xgboost==3.2.1` distribution; both
  expose `3.2.0` and then `3.3.0`.
- Full pytest: `306 passed, 1 failed, 3 warnings` in `22.8s`.
- The sole failure is the frozen XGBoost version assertion.

## Decisions

- `BLOCKED_DEPENDENCY`.
- Do not substitute `3.1.3`, `3.2.0`, `3.3.0`, another library, or a workaround.
- Do not read the prepared/reference artifacts for outcome execution.
- Do not run ordinal 010 control or ordinal 011 LambdaMART.
- Ledger ordinals 010/011 remain unviewed; cumulative evaluated count remains 7.

## Forbidden access confirmation

- V3-E outcomes: not accessed.
- V2F5/V2F6: not materialized or accessed.
- Reserved post-2026-07-31 V2 fresh-forward outcomes: not accessed.
- `FORWARD_OUTCOME_ACCESS_STARTED`: not written.
- V3-D remained blocked/unscored.
- Integration, calibration, Stage 6, IDX-VAL-002, execution/PnL, paper/live,
  and main merge: not started.

## Validation run

```text
python -m pytest -c pyproject.toml tests
306 passed, 1 failed, 3 warnings in 22.8s
```

## Required next action

Make exact `xgboost==3.2.1` installable in the local Python environment, rerun
full pytest, then resume the unchanged frozen V3-E handoff only after pytest
passes.

# Handoff: Ranking V4-3 target / execution freeze V1

from: ChatGPT
to: local execution operator / ChatGPT reviewer
task_id: IDX-RANKING-V4-3-TARGET-EXECUTION-FREEZE-V1
branch: `research/idx-ranking-v4-3-target-execution-freeze-v1`
status: `V4_3_EXECUTION_PATH_FROZEN_PENDING_LOCAL_SYNTHETIC_VALIDATION_PIT_REFRESH_AND_CA_CONTINUITY`

## What is already implemented

The branch freezes, before historical target access:

- exact V4 t+1 / H5 / H10 target ledger semantics;
- fail-closed market/data/continuity states;
- accepted-Open Geometry3 construction;
- PIT-safe 25-feature control construction with listing-domain rows removed before rolling/context;
- exact Control/Challenger HGB pipelines and date weighting;
- date-centric H5/H10/consensus evaluator, Top30/Bottom30/no-refill logic, fold admission, block bootstrap, paired deltas, and frozen threshold mapping;
- deterministic disjoint score-tie behavior;
- outcome-blind PIT-remediated support refresh;
- exact runtime-bound execution-code manifest capture.

Detailed checkpoint:

`docs/checkpoints/2026-08-17_RANKING_V4_3_TARGET_EXECUTION_PREFIT_FREEZE.md`

## Local-only inputs required next

Authoritative bytes are outside the GitHub connector and must be read locally:

- research artifact root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809`
- accepted Open derivative root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_tradingview_derivative_v1_20260811`
- verified Open CA overlay root:
  `D:\Documents\Project\idx-open-ca-scale-reconstruction-20260817-v1`
- authoritative security master source, expected:
  `D:\Documents\Project\idx-trade-data-gate-20260808u\certification\security_master.csv`
  with required SHA-256 `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240`.

If the security-master path does not exist, do not substitute another copy merely by name. Locate an exact SHA-identical copy or stop and report the blocker.

## Required local sequence

1. Fetch latest canonical `origin/main:coordination/TEAM_STATUS.md`. Update/claim only the V4 target/execution freeze row as ACTIVE; preserve all other rows.
2. Checkout/pull this exact branch and keep scientific configs unchanged.
3. Run focused tests:

```text
python -m pytest tests/test_ranking_v4_3_preregistration.py tests/test_ranking_v4_3_prefit_runtime.py tests/test_ranking_v4_3_target_execution.py tests/test_ranking_v4_3_features.py tests/test_ranking_v4_3_model_eval.py tests/test_ranking_v4_3_evaluator_ties.py tests/test_ranking_v4_3_execution_code_capture.py
```

4. Run `py_compile` for:

```text
src/idx_trade/ranking_v4_3_target_execution.py
src/idx_trade/ranking_v4_3_features.py
src/idx_trade/ranking_v4_3_model_eval.py
scripts/run_v4_3_pit_support_refresh.py
scripts/capture_v4_3_execution_code_manifest.py
```

5. Run `git diff --check`. Worktree must be clean before immutable captures.
6. Run only the outcome-blind PIT support refresh:

```text
python scripts/run_v4_3_pit_support_refresh.py \
  --artifact-root "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809" \
  --open-derivative-root "D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_tradingview_derivative_v1_20260811" \
  --overlay-root "D:\Documents\Project\idx-open-ca-scale-reconstruction-20260817-v1" \
  --security-master "D:\Documents\Project\idx-trade-data-gate-20260808u\certification\security_master.csv" \
  --repo-root . \
  --output-dir "D:\Documents\Project\idx-v4-3-pit-support-refresh-20260817-v1"
```

7. If verdict is NOT `V4_3_PIT_REMEDIATED_SUPPORT_PRESERVES_FROZEN_6X100`, STOP. Record the exact identity/support blocker. Do not capture execution manifest and do not inspect targets.
8. If PIT verdict passes, ensure worktree is clean, then run only:

```text
python scripts/capture_v4_3_execution_code_manifest.py \
  --repo-root . \
  --output-dir "D:\Documents\Project\idx-v4-3-execution-code-freeze-20260817-v1"
```

9. Promote only small PIT-support summary/identity/manifests and execution-code manifest/checkpoint metadata. Do not promote large panel bytes.
10. Update only the existing canonical TEAM_STATUS row to REVIEW if both local steps pass, otherwise BLOCKED with exact reason. Push and stop.

## Strict prohibitions

Do NOT:

- materialize historical R5/R10;
- materialize historical target ranks;
- fit the historical V4 Control or Challenger;
- generate historical V4 predictions;
- compute IC, Top30, spread, raw-return diagnostics, bootstrap performance, or promotion verdicts;
- call a market-data or Corporate Action provider;
- acquire new Corporate Action data;
- alter target, folds, learner, feature list, thresholds, Top30, observability gates, tie-break, or promotion rules;
- access protected/fresh-forward outcomes.

## Remaining blocker after successful local validation

Even if PIT support and execution-code capture pass, V4 historical target access remains blocked by market-wide forward-price Corporate Action continuity. Existing accepted CA work does not yet provide a complete effective-date/no-event ledger for all mechanical price-basis events.

Stop for ChatGPT review after the bounded local sequence.

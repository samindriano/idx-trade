# Handoff: Final V3-B Structure-Lite Refit / Forward Runtime Local Validation

Date: 2026-08-10 (Asia/Jakarta)
Status: **AUTHORIZED WINDOWS-LOCAL PYTEST + ONE FINAL HISTORICAL REFIT ONLY — NO FRESH OUTCOME ACCESS**

## Goal

Pull the latest `research/idx-ranking-v2-spec-v1`, validate the newly implemented final V3-B runtime, run exactly one final historical Structure-Lite refit on the frozen resolved-primary-H10 table, freeze/hash its artifacts, document the result, and stop.

This task must not inspect post-2026-07-31 outcomes or produce a fresh-forward verdict.

## Mandatory reads

1. `docs/CURRENT_STATUS.md`
2. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
3. `docs/checkpoints/2026-08-10_RANKING_V4_FINAL_ALPHA_REVIEW_CLOSED.md`
4. `docs/RANKING_V3_FINAL_FORWARD_SPEC_V1.md`
5. `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_FORWARD_SPEC_REVIEW_PASS.md`
6. `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REFIT_FORWARD_RUNTIME_IMPLEMENTED_PRE_LOCAL.md`
7. `src/idx_trade/ranking_v3_forward_runtime.py`
8. `tests/test_ranking_v3_forward_runtime.py`

Acknowledge before execution that:

- V4 alpha research is closed;
- final ranker is exact `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- no model/feature/threshold selection is permitted;
- sessions `1225..1250` may be used for final training only, never as another validation slice;
- fresh-forward labels/outcomes and the real global marker remain prohibited.

## Repository preflight

From the repository root:

```powershell
git fetch origin
git checkout research/idx-ranking-v2-spec-v1
git pull --ff-only origin research/idx-ranking-v2-spec-v1
git status --short
$HEAD = git rev-parse HEAD
$UPSTREAM = git rev-parse origin/research/idx-ranking-v2-spec-v1
python -m pytest
```

Require:

- clean tree before local artifact work;
- `$HEAD -eq $UPSTREAM`;
- full pytest with zero failures.

The previous tree had `357 passed`; new focused tests were added afterward, so do **not** require exactly 357. A higher count is expected. Zero failures is the gate.

If pytest fails:

- a narrow mechanical engineering correction is allowed only when it restores the frozen documented semantics and does not alter any feature/model/fold/metric/outcome rule;
- add a focused regression test;
- rerun full pytest;
- if the fix would change research semantics, STOP and return the failure without refitting.

## Frozen local inputs

Research-store root:

```powershell
$ROOT = "D:\Documents\Project\idx-trade-data-gate-20260808v"
```

Resolve exact files and verify SHA-256 before the refit.

### Signal panel

Known path:

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet
```

Required SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

### Official calendar

Known path:

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv
```

Required SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

### Security master

Known path:

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260.csv
```

Required SHA-256:

`9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`

### Frozen V2 prepared table

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet
```

Required SHA-256:

`522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`

### Frozen V2 prepared manifest

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_cache_manifest.json
```

Required SHA-256:

`6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`

### Final V3-B forward spec

Repository path:

`docs\RANKING_V3_FINAL_FORWARD_SPEC_V1.md`

Required Git blob:

`024f1919de8d5ea4e2e9933a9e4c1a1ef9bbe4f4`

Exact 33-feature-order SHA-256:

`100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`

Stop if any identity fails.

## One authorized final refit

Use a new empty output directory, for example:

```powershell
$OUT = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_b_final_refit_20260810_001"
```

Run exactly:

```powershell
python -m idx_trade.ranking_v3_forward_runtime final-refit `
  --panel "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet" `
  --calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" `
  --security-master "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260.csv" `
  --prepared-table "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet" `
  --prepared-manifest "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_cache_manifest.json" `
  --spec "docs\RANKING_V3_FINAL_FORWARD_SPEC_V1.md" `
  --output-dir $OUT `
  --code-commit $HEAD
```

Do not run the command twice. If it exits after creating a partial nonempty output directory, STOP and report rather than deleting/retrying the directory unless the failure is proven to have occurred strictly before model fitting and MAIN/ChatGPT later authorizes a retry.

## Required final-refit invariants

The run must report:

- status `RANKING_V3_B_FINAL_REFIT_FROZEN`;
- architecture `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- rows `292633`;
- tickers `737`;
- signal-session range `20..1250`;
- feature-order SHA `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- exact source/cache/spec identities;
- no orphan or duplicate training row;
- no infinity in Structure-Lite features;
- training table SHA-256;
- final model SHA-256;
- final model-manifest SHA-256;
- summary SHA-256;
- `historical_performance_metrics_computed=false`;
- `fresh_forward_outcomes_accessed=false`;
- `forward_outcome_access_marker_written=false`.

The output must contain at least:

- `ranking_v3_b_structure_lite_final_training_table.parquet`;
- `ranking_v3_b_structure_lite_final.joblib`;
- `ranking_v3_b_structure_lite_final_manifest.json`;
- `ranking_v3_b_structure_lite_final_summary.json`.

## Verify artifact pair

After the single successful fit, call `verify_final_v3_refit_artifacts` using the exact model/manifest hashes emitted by the run. Require `valid=true`.

This verification is outcome-blind and does not constitute a second model fit.

## Documentation

After successful verification, update only research continuity/documentation as needed:

- `docs/CURRENT_STATUS.md`;
- `docs/PROJECT_LEDGER.md`;
- create `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REFIT_RUNTIME_RESULT.md`;
- create `coordination/handoffs/IDX-RANKING-V3-FINAL-REFIT-FORWARD-RUNTIME-LOCAL-RESULT.md`.

Record exact local paths, artifact hashes, runtime/profile, final pytest, branch/head, and all boundary flags.

Commit and push documentation plus any narrowly necessary semantics-preserving test/code correction. Do not commit local model/data artifacts.

## HARD STOP

After the final refit is frozen and documented, STOP.

Do **not**:

- construct or inspect a post-2026-07-31 outcome/label table;
- write the real `FORWARD_OUTCOME_ACCESS_STARTED` marker;
- run `evaluate_frozen_forward_block` on real data;
- compute fresh PR/ROC/Q5-Q1;
- score sessions `1225..1250` as a validation slice;
- create another alpha candidate or V4 rescue;
- calibrate probability;
- start Path-Risk automatically in this task;
- start Stage 6 / `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge.

## Return to ChatGPT

Return:

1. branch + final HEAD/upstream + clean state;
2. full pytest result;
3. all five frozen input identities and spec blob verification;
4. training table rows/tickers/session range + SHA;
5. model path + SHA;
6. manifest path + SHA;
7. summary SHA;
8. artifact verification result;
9. runtime/profile;
10. explicit confirmation that zero historical performance metric was computed for the final refit, no real fresh-forward outcome was accessed, and the global marker remains unwritten.

# Handoff: Path Risk V1 PR-001 F1-F4 Discovery Run

Date: 2026-08-10 (Asia/Jakarta)
Status: **RUN-ONLY LOCAL EXECUTION — NO SOURCE EDITS**

## Goal

Pull the latest `research/idx-ranking-v2-spec-v1`, run full pytest, and if it passes with zero failures execute exactly one real historical Path Risk V1 PR-001 discovery run on F1-F4 using the already-implemented runner.

Do not implement or modify research code in this task. Return the local result to ChatGPT for interpretation and repository documentation.

## Mandatory reads

1. `docs/CURRENT_STATUS.md`
2. `docs/PATH_RISK_V1_SPEC.md`
3. `docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_CACHE_AUDIT_RESULT.md`
4. `docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_CACHE_REVIEW_PASS.md`
5. `src/idx_trade/path_risk_v1.py`
6. `src/idx_trade/path_risk_v1_discovery_run.py`
7. `tests/test_path_risk_v1.py`
8. `tests/test_path_risk_v1_discovery_run.py`
9. `docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_IMPORT_PREFLIGHT_BLOCK.md`

Acknowledge:

- final alpha ranker remains frozen V3-B Structure-Lite;
- Path Risk is a separate lane;
- PR-001 has not yet been viewed;
- F5/F6 Path Risk and fresh-forward outcomes are still sealed;
- source/model/spec changes are prohibited in this local task.

## Preflight

This repository uses a `src/` package layout. `pytest` injects `src` through `pyproject.toml`, but a bare `python -m ...` does not. The first local execution attempt therefore resolved `idx_trade` from an older Codex worktree and stopped before any outcome access. For this rerun, the current checkout's `src` directory is explicitly pinned for the entire PowerShell process.

```powershell
git fetch origin
git checkout research/idx-ranking-v2-spec-v1
git pull --ff-only origin research/idx-ranking-v2-spec-v1
git status --short
$HEAD = git rev-parse HEAD
$UPSTREAM = git rev-parse origin/research/idx-ranking-v2-spec-v1

# Replace any inherited PYTHONPATH so Python cannot resolve idx_trade from a stale worktree.
$REPO_ROOT = (Resolve-Path .).Path
$SRC_ROOT = (Resolve-Path .\src).Path
$env:PYTHONPATH = $SRC_ROOT

# Fail closed unless both the package and the discovery runner resolve from THIS checkout.
python -c "import pathlib, idx_trade, idx_trade.path_risk_v1_discovery_run as r; root=pathlib.Path(r'$REPO_ROOT').resolve(); pkg=pathlib.Path(idx_trade.__file__).resolve(); runner=pathlib.Path(r.__file__).resolve(); print('idx_trade=', pkg); print('runner=', runner); assert root in pkg.parents; assert root in runner.parents"

python -m pytest
```

Require:

- clean working tree before execution;
- `$HEAD -eq $UPSTREAM`;
- `idx_trade` and `path_risk_v1_discovery_run` both resolve below the current `$REPO_ROOT`;
- full pytest with `0 failed`.

If import verification or pytest fails, STOP and return the exact failure. Do not patch code locally.

## Frozen local inputs

### Feature cache

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_feature_cache_prepare_20260810_001\path_risk_v1_discovery_feature_cache.parquet
```

SHA-256:

`74c300390dce542dad95ae204dd7663f5f780b09dd33c3514c5dd264f15cca08`

### Feature-cache manifest

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_feature_cache_prepare_20260810_001\path_risk_v1_discovery_feature_cache_manifest.json
```

SHA-256:

`054ccff7676a744871b1f82a5b263898f9fa53c2d1ae1ac20a5659485466bed0`

### Frozen H10 labels

Expected local artifact:

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\research_label_equivalence_benchmark_20260809\fast_h10_labels.parquet
```

Required SHA-256:

`a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`

If that exact path is absent, locate the local Parquet artifact by the exact SHA under the research-store root. Do not substitute an unverified label file.

### Signal panel

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet
```

SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

### Official calendar

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv
```

SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

## One authorized run

Use a new empty output directory:

```powershell
$OUT = "D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_run_20260810_001"
```

Run exactly once in the **same PowerShell process where `$env:PYTHONPATH = $SRC_ROOT` was set**:

```powershell
python -m idx_trade.path_risk_v1_discovery_run `
  --feature-cache "D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_feature_cache_prepare_20260810_001\path_risk_v1_discovery_feature_cache.parquet" `
  --feature-manifest "D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_feature_cache_prepare_20260810_001\path_risk_v1_discovery_feature_cache_manifest.json" `
  --h10-labels "D:\Documents\Project\idx-trade-data-gate-20260808v\research_label_equivalence_benchmark_20260809\fast_h10_labels.parquet" `
  --panel "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet" `
  --calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" `
  --output-dir $OUT `
  --code-commit $HEAD
```

If the label path had to be resolved by exact SHA, substitute only that verified path in `--h10-labels`.

Do not run the command twice. If the process errors after creating a nonempty output directory, STOP and return the failure boundary; do not delete/retry.

## Required outputs to report

Return, without editing repo files:

1. branch, final HEAD/upstream, clean state;
2. exact `idx_trade.__file__` and discovery-runner `__file__` import paths from preflight;
3. full pytest result;
4. exact verified input hashes;
5. target rows and target status composition;
6. feature/target join coverage;
7. per-fold F1-F4:
   - train rows;
   - validation rows/dates/tickers;
   - training q75 baseline;
   - baseline pinball;
   - model pinball;
   - relative pinball improvement;
   - Spearman;
   - q75 empirical coverage/error;
   - Q1/Q5 realized adverse excursion and spread;
   - Q1/Q5 stop-touch rates;
   - prediction finite rate / unique prediction count;
8. exact frozen gate checks and final verdict;
9. all artifact hashes, including target/model-table/metrics/predictions/summary and per-fold model hashes;
10. runtime total + per fold;
11. explicit confirmation that:
   - only F1-F4 Path Risk outcomes were materialized/evaluated;
   - no Path Risk F5/F6 outcome was read into the run frames;
   - no post-2026-07-31 outcome was accessed;
   - `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
   - ranker unchanged;
   - no risk-veto/integration rule was created.

## Hard stop

After returning the report, STOP.

Do not:

- edit/commit/push source or docs;
- rerun PR-001 after outcome access begins;
- access F5/F6 Path Risk outcomes;
- change quantile/model/features/folds/gates;
- create rescue candidates;
- create alpha+risk integration rules;
- access fresh-forward outcomes;
- start calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge.

# Handoff: Path Risk V2 PR-002/PR-003 F1-F4 Discovery Run

Date: 2026-08-11 (Asia/Jakarta)
Status: **RUN-ONLY LOCAL EXECUTION — NO SOURCE/DOC EDITS; F5/F6 PROHIBITED**

## Goal

Run the frozen Path Risk V2 F1-F4 development comparison exactly once after a
clean full-test preflight.

Candidates:

- PR-002 `PATH-RISK-V2-STOP-H10-HGB-002`;
- PR-003 `PATH-RISK-V2-DISCRETE-CR-HGB-003`.

This task may view only the already-consumed Path Risk development period
through signal session `984`.  It must not access Path Risk F5/F6 or any
post-2026-07-31 fresh-forward outcome.

## Mandatory reads

1. `docs/CURRENT_STATUS.md`
2. `docs/PATH_RISK_V2_SPEC.md`
3. `docs/PATH_RISK_V2_LEDGER.md`
4. `docs/checkpoints/2026-08-11_PATH_RISK_V2_IMPLEMENTED_PRE_OUTCOME.md`
5. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
6. `src/idx_trade/path_risk_v2.py`
7. `src/idx_trade/path_risk_v2_discovery_run.py`
8. `tests/test_path_risk_v2.py`
9. `tests/test_path_risk_v2_discovery_run.py`

Acknowledge before running:

- PR-001 remains permanently V1 FAIL_CLOSE;
- PR-002/PR-003 are new V2 ordinals, currently unviewed;
- V2 F1-F4 are development only;
- F5/F6 are sealed even if one V2 candidate wins;
- final alpha ranker remains frozen V3-B Structure-Lite;
- no risk-veto, reranking, sizing or integration rule is authorized.

## Import-path preflight

The previous Path Risk V1 attempt exposed a stale-worktree `PYTHONPATH` risk.
Force the current checkout's `src` directory and verify module resolution before
pytest or the real run.

```powershell
git fetch origin
git checkout research/idx-ranking-v2-spec-v1
git pull --ff-only origin research/idx-ranking-v2-spec-v1
git status --short

$HEAD = git rev-parse HEAD
$UPSTREAM = git rev-parse origin/research/idx-ranking-v2-spec-v1
$REPO_ROOT = (Resolve-Path .).Path
$SRC_ROOT = (Resolve-Path .\src).Path
$env:PYTHONPATH = $SRC_ROOT

python -c "import pathlib, idx_trade, idx_trade.path_risk_v2 as v2, idx_trade.path_risk_v2_discovery_run as r; root=pathlib.Path.cwd().resolve(); print(idx_trade.__file__); print(v2.__file__); print(r.__file__); assert root in pathlib.Path(idx_trade.__file__).resolve().parents; assert root in pathlib.Path(v2.__file__).resolve().parents; assert root in pathlib.Path(r.__file__).resolve().parents"

python -m pytest
```

Require:

- `$HEAD -eq $UPSTREAM`;
- clean working tree;
- all three Python module paths resolve from this checkout;
- full pytest has `0 failed`.

If any preflight fails, STOP.  Do not patch locally.

## Frozen local inputs

### PR-001 joined F1-F4 model table

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_run_20260810_001\path_risk_v1_discovery_model_table.parquet
```

Required SHA-256:

`b66fc7e40f18940ae9db418331a421e0f36d23b86597500b1d3ba73a8e3777fe`

Required facts:

- `252,198` rows;
- max signal session `984`;
- contains only the already-viewed Path Risk F1-F4 development population.

### Official calendar

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv
```

Required SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

### Frozen V2 spec

Repo file:

```text
docs\PATH_RISK_V2_SPEC.md
```

Required Git blob:

`6d171d3f492b9cd15e0a176428eb9d6e4f6c20c5`

## One authorized run

Use a new empty output directory:

```powershell
$OUT = "D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v2_discovery_run_20260811_001"
```

Run exactly once:

```powershell
python -m idx_trade.path_risk_v2_discovery_run `
  --v1-model-table "D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_run_20260810_001\path_risk_v1_discovery_model_table.parquet" `
  --calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" `
  --spec "docs\PATH_RISK_V2_SPEC.md" `
  --output-dir $OUT `
  --code-commit $HEAD
```

Do not run this command twice.

If the process fails after the real runner starts and the output directory is
nonempty, STOP and return the exact failure boundary.  Do not delete/retry until
ChatGPT reviews whether an ordinal was partially consumed.

## Required report

Return to ChatGPT, without editing/pushing repo files:

1. branch, HEAD/upstream and clean state;
2. exact module resolution paths;
3. full pytest result;
4. verified V1 model-table/calendar/spec identities;
5. model-table rows/status composition/stop-touch prevalence;
6. for each fold, base-rate and alpha-only comparator:
   - log loss;
   - Brier;
   - ROC-AUC;
   - PR-AUC;
   - ECE;
7. for PR-002 and PR-003 on F1-F4:
   - log loss and Brier;
   - relative improvements vs base rate;
   - relative improvements vs alpha-only;
   - ROC-AUC / PR-AUC;
   - ECE;
   - Q1/Q5 stop-touch rates and Q5-Q1 spread;
   - Spearman vs adverse excursion;
   - finite rate / unique predictions;
8. PR-003 additionally:
   - mean H3/H5/H10 stop CIF;
   - mean H10 TP CIF;
   - mean H10 survival;
   - max probability-mass error;
   - expanded training rows per fold;
9. exact gate checks for both candidates;
10. final V2 F1-F4 verdict and selected winner, if any;
11. all model/comparator/metrics/prediction/summary hashes;
12. runtime total and per-fold comparator/PR-002/PR-003 timings;
13. explicit confirmations:
   - no session `985+` outcome materialized;
   - no Path Risk F5/F6 access;
   - no fresh-forward access;
   - `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
   - final V3-B ranker unchanged;
   - no risk integration/veto/sizing rule created.

## Hard stop

After returning the report, STOP.

Do not:

- edit/commit/push source or docs;
- rerun PR-002/PR-003;
- access Path Risk F5/F6;
- change candidate definitions/features/gates/selection rule;
- create PR-004 or rescue candidates;
- calibrate post hoc;
- create alpha+risk integration/reranking/veto/sizing rules;
- access fresh-forward outcomes or write the forward marker;
- start execution/PnL/Kelly/paper/live work from this result.

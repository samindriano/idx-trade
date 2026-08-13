# Handoff: Ranking V4-B + V4-C Frozen First-Pass Outcome Run

Date: 2026-08-10 (Asia/Jakarta)
Status: **AUTHORIZED HISTORICAL-DEVELOPMENT OUTCOME RUN — EXACT FROZEN B/C ONLY**

## Goal

Execute the already-frozen V4-C and V4-B first-pass historical-development runners without changing either design and without inspecting the first family's outcome before the second family has completed.

Controlling authorization:

`docs/checkpoints/2026-08-10_RANKING_V4_B_C_FIRST_PASS_OUTCOME_AUTHORIZED.md`

The newest authorization supersedes older `CURRENT_STATUS.md` text that still says V4-C cache/audit is the immediate next action.

## Mandatory reads

1. `docs/CURRENT_STATUS.md`
2. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
3. `docs/checkpoints/2026-08-10_RANKING_V4_B_PRICE_PATH_AUDIT_REVIEW_PASS.md`
4. `docs/checkpoints/2026-08-10_RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_AUDIT_REVIEW_PASS.md`
5. `docs/checkpoints/2026-08-10_RANKING_V4_B_C_FIRST_PASS_OUTCOME_AUTHORIZED.md`
6. `docs/RANKING_V4_B_PRICE_PATH_SPEC_V1.md`
7. `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md`
8. `src/idx_trade/ranking_v4_price_path_run.py`
9. `src/idx_trade/ranking_v4_cross_sectional_context_run.py`
10. `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`

Do not reinterpret older pre-outcome handoffs as a prohibition after reading the new explicit authorization.

## Repository preflight

From the IDX Trade repo root:

```powershell
git fetch origin
git checkout research/idx-ranking-v2-spec-v1
git pull --ff-only origin research/idx-ranking-v2-spec-v1
git status --short
$HEAD = git rev-parse HEAD
python -m pytest
```

Require:

- branch `research/idx-ranking-v2-spec-v1`;
- clean working tree before scoring;
- local HEAD exactly equals upstream after pull;
- full pytest has zero failures.

Do not score if preflight fails.

## Local research-store root

```powershell
$ROOT = "D:\Documents\Project\idx-trade-data-gate-20260808v"
```

All local input artifacts must be resolved by exact SHA-256, not filename alone.

## Frozen V4-C cache

Required cache SHA-256:

`480f09488c89128859921abe0617e51d04ac05d0ddfc42fb8f4d0c063f2b255e`

Required manifest SHA-256:

`33ba2b39ce10476bea0566b2d240806a9d258ebe8c5f1b61733a539a397b7737`

Expected preparation directory is normally:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_c_cross_sectional_context_prepare_20260810_001\`

but SHA identity is authoritative. Resolve:

- `ranking_v4_c_cross_sectional_context_prepared_cache.parquet`;
- `ranking_v4_c_cross_sectional_context_prepared_cache_manifest.json`.

Required spec Git blob:

`43f222f31c7c0ea15e870d22b066aae95858c81f`.

## Frozen V4-B cache

Required cache SHA-256:

`8c59200d284e73867a3ff3566473f7dc7dd4aa0a2bfd42917ef4e08c761d1c68`

Required manifest SHA-256:

`d30c7e4f0841bbddd479fdc0b8c62b1028dcf8f107277b5a8a250d9725243b2f`

Known preparation directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_b_price_path_prepare_20260810_001\`

Resolve:

- `ranking_v4_b_price_path_prepared_cache.parquet`;
- `ranking_v4_b_price_path_prepared_cache_manifest.json`.

Required spec Git blob:

`a750c28831b95b1c88640c5879289da5f2c05446`.

## Frozen V3-B reference artifacts

Use exactly these artifacts and verify every SHA before either outcome run:

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_run_20260810_run1\ranking_v3_b_structure_lite_f1_f4_metrics.csv
SHA 0a6919a22669c14db272cc12ff70081d50ea53139f591c7faf2be2c43d321357

D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_run_20260810_run1\ranking_v3_b_structure_lite_f1_f4_predictions.parquet
SHA c7761dd0bd93340381b28234537bf7a42e829eae0f214ec8173d8bc1f6f2e4e1

D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_run_20260810_001\ranking_v3_final_structure_lite_f5_f6_metrics.csv
SHA 5e758e468cf883212fdb11c64d63f8ab3cf86c20a04a60edbc651205bc8f6d25

D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_run_20260810_001\ranking_v3_final_structure_lite_f5_f6_predictions.parquet
SHA 64cf1c04640740c5906db03e1ba86290790904daca2971e61c00212de893715b
```

Both runners have hard-coded reference-hash checks; still verify them before execution.

## Fixed outcome-opening sequence

The sequence is frozen to prevent B/C cross-adaptation.

### 1. Create new empty output directories

Example:

```powershell
$COUT = "$ROOT\ranking_v4_c_first_pass_run_20260810_001"
$BOUT = "$ROOT\ranking_v4_b_first_pass_run_20260810_001"
$CSTDOUT = "$ROOT\ranking_v4_c_first_pass_run_20260810_001.stdout.json"
$BSTDOUT = "$ROOT\ranking_v4_b_first_pass_run_20260810_001.stdout.json"
```

Use different suffixes if any path already exists. Never overwrite prior artifacts.

### 2. Execute V4-C first, but do not inspect outcome

Run exact control+019:

```powershell
python -m idx_trade.ranking_v4_cross_sectional_context_cli run `
  --cache $V4C_CACHE `
  --cache-manifest $V4C_MANIFEST `
  --spec "docs\RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md" `
  --v3-f1-f4-metrics $V3_F1F4_METRICS `
  --v3-f1-f4-predictions $V3_F1F4_PREDICTIONS `
  --v3-f5-f6-metrics $V3_F5F6_METRICS `
  --v3-f5-f6-predictions $V3_F5F6_PREDICTIONS `
  --output-dir $COUT `
  --code-commit $HEAD *> $CSTDOUT
```

Record exit code only. Do **not** open `$CSTDOUT`, summary, metrics, paired, predictions, verdict, or models yet.

If this command exits nonzero, stop immediately. Report the exact exception, files materialized, and whether any challenger scores/outcomes may already have been computed. Do not rerun and do not start V4-B.

### 3. Execute V4-B without inspecting V4-C

Only if V4-C exited zero, run exact control+B1+B2:

```powershell
python -m idx_trade.ranking_v4_price_path_cli run `
  --cache $V4B_CACHE `
  --cache-manifest $V4B_MANIFEST `
  --spec "docs\RANKING_V4_B_PRICE_PATH_SPEC_V1.md" `
  --v3-f1-f4-metrics $V3_F1F4_METRICS `
  --v3-f1-f4-predictions $V3_F1F4_PREDICTIONS `
  --v3-f5-f6-metrics $V3_F5F6_METRICS `
  --v3-f5-f6-predictions $V3_F5F6_PREDICTIONS `
  --output-dir $BOUT `
  --code-commit $HEAD *> $BSTDOUT
```

Do not inspect V4-C while V4-B is running. If V4-B exits nonzero, stop and report exact partial state. Do not rerun after opening any challenger result.

### 4. Only after both exit zero, inspect both

Now read both summaries/verdicts/metrics/paired/top-decile-overlap/runtime artifacts.

The runners themselves determine PASS/FAIL from the frozen gate. Do not reinterpret or soften thresholds.

## Required result report

For V4-C report:

- exact control-equivalence status and max score/metric diffs;
- per-fold control and 019 metrics: prevalence, PR-AUC, PR delta, ROC-AUC, Q1, Q5, Q5-Q1, top-decile TP rate/lift;
- per-fold paired PR/ROC/Q5-Q1/top-decile-lift changes;
- full gate detail;
- 019 final PASS/FAIL;
- top-decile Jaccard/entrants/exits by fold;
- runtime and artifact hashes.

For V4-B report separately for 016 and 017:

- exact control-equivalence status and max score/metric diffs;
- per-fold control/B1/B2 metrics;
- per-fold paired PR/ROC/Q5-Q1/top-decile-lift changes;
- full gate detail for each challenger;
- final PASS/FAIL for 016 and 017;
- top-decile overlap diagnostics;
- survivors list;
- runtime and artifact hashes.

Also report:

- branch and final HEAD;
- full pytest result;
- all input/cache/reference hashes verified;
- candidate ordinals viewed;
- cumulative historical evaluated-candidate count after the completed runs (`17` if all 015..019 were viewed);
- `post_1224_materialized=false`;
- `fresh_forward_accessed=false`;
- `FORWARD_OUTCOME_ACCESS_STARTED` still unwritten.

## Repository documentation after successful result capture

After both results have been inspected, update and commit/push:

- `docs/CURRENT_STATUS.md`;
- `docs/PROJECT_LEDGER.md`;
- `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`;
- one or two dated result checkpoints covering V4-B and V4-C;
- `coordination/handoffs/IDX-RANKING-V4-B-C-FIRST-PASS-OUTCOME-RESULT.md`.

Preserve all PASS and FAIL outcomes permanently. No candidate disappears from the denominator.

## Hard stop

After documentation and push, stop for ChatGPT review.

Do not:

- change either V4-B or V4-C frozen specification;
- rerun a failed challenger after viewing its outcome;
- create B1+B2 integration;
- create B/C cross-family integration;
- start another V4 family;
- use session `1225+`;
- access post-2026-07-31 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, portfolio construction, paper/live, or main merge.

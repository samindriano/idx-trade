# Handoff — IDX Ranking V4-A Participation First-Pass Atomic Run

Date: 2026-08-10 (Asia/Jakarta)
Status: **AUTHORIZED — ONE ATOMIC CONTROL+A1+A2 HISTORICAL-DEVELOPMENT RUN**

## Objective

Execute the already-frozen V4-A Participation first-pass comparison exactly once on Windows-local historical development data:

- ordinal `012`: exact final V3-B control;
- ordinal `013`: A1 Impact/Absorption;
- ordinal `014`: A2 Persistent Directional Participation.

A1 and A2 must be scored in the same runner invocation. Do not inspect one challenger and then adapt or decide whether to execute the other.

No A1+A2 integration is allowed in this run.

## Required reads

Before any command, pull the latest branch and read:

1. `docs/CURRENT_STATUS.md`
2. `docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_CACHE_AUDIT_RESULT.md`
3. `docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RUN_AUTHORIZED.md`
4. `docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`
5. `docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_REVIEW_ADDENDUM_V1.md`
6. `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`
7. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
8. `src/idx_trade/ranking_v4_participation_run.py`
9. `tests/test_ranking_v4_participation.py`
10. `tests/test_ranking_v4_participation_run.py`

## Repository preflight

From the repository root:

```powershell
git fetch origin
git checkout research/idx-ranking-v2-spec-v1
git pull --ff-only origin research/idx-ranking-v2-spec-v1
git status --short
$HEAD = git rev-parse HEAD
python -m pytest
```

Require:

- branch exactly `research/idx-ranking-v2-spec-v1`;
- clean tree before execution;
- local/remote synchronized;
- full pytest PASS.

If pytest fails, STOP before model scoring unless the issue is an unambiguous engineering-only defect that does not alter frozen feature formulas, candidate definitions, data identities, fold contract, scoring semantics, or gates. Any permitted engineering correction must be committed/pushed and followed by another full pytest PASS before execution.

## Frozen V4-A input cache

Prepared cache directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_prepare_20260810_001\`

Required files:

```powershell
$CACHE = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_prepare_20260810_001\ranking_v4_a_participation_prepared_cache.parquet"
$MANIFEST = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_prepare_20260810_001\ranking_v4_a_participation_prepared_cache_manifest.json"
```

Required SHA-256:

- cache: `a487e14625942cba849b499730113cf8d0f9b3f08e866177c79642079cef6aab`;
- manifest: `b9f15e5363e2ea0a2f912fe31a563fc45ebf7ed4788ee524540b1cdb41d308cc`.

Verify before run:

```powershell
(Get-FileHash $CACHE -Algorithm SHA256).Hash.ToLower()
(Get-FileHash $MANIFEST -Algorithm SHA256).Hash.ToLower()
```

The manifest must still report:

- `outcome_metrics_computed=false`;
- `fresh_forward_accessed=false`;
- `post_1224_materialized=false`;
- `integration_candidate_materialized=false`.

Frozen spec:

```powershell
$SPEC = "docs\RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md"
```

Frozen spec Git blob identity: `e32fa69596291f418ae797613da219bd0d3cf69c`.

## Frozen V3-B reference artifacts

The V4-A runner must verify these SHA-256 identities internally.

### F1-F4 Structure-Lite reference

Directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_run_20260810_run1\`

Files:

```powershell
$F1F4_METRICS = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_run_20260810_run1\ranking_v3_b_structure_lite_f1_f4_metrics.csv"
$F1F4_PRED = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_run_20260810_run1\ranking_v3_b_structure_lite_f1_f4_predictions.parquet"
```

Required hashes:

- metrics: `0a6919a22669c14db272cc12ff70081d50ea53139f591c7faf2be2c43d321357`;
- predictions: `c7761dd0bd93340381b28234537bf7a42e829eae0f214ec8173d8bc1f6f2e4e1`.

### F5-F6 final late-development reference

Directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_run_20260810_001\`

Files:

```powershell
$F5F6_METRICS = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_run_20260810_001\ranking_v3_final_structure_lite_f5_f6_metrics.csv"
$F5F6_PRED = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_run_20260810_001\ranking_v3_final_structure_lite_f5_f6_predictions.parquet"
```

Required hashes:

- metrics: `5e758e468cf883212fdb11c64d63f8ab3cf86c20a04a60edbc651205bc8f6d25`;
- predictions: `64cf1c04640740c5906db03e1ba86290790904daca2971e61c00212de893715b`.

Verify all four paths/hashes before executing. SHA identity is authoritative if a local path differs.

## One atomic first-pass command

Use one new/empty output directory, for example:

```powershell
$OUT = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_first_pass_run_20260810_001"
```

Run exactly one invocation:

```powershell
python -m idx_trade.ranking_v4_participation_run `
  --cache $CACHE `
  --cache-manifest $MANIFEST `
  --spec $SPEC `
  --v3-f1-f4-metrics $F1F4_METRICS `
  --v3-f1-f4-predictions $F1F4_PRED `
  --v3-f5-f6-metrics $F5F6_METRICS `
  --v3-f5-f6-predictions $F5F6_PRED `
  --output-dir $OUT `
  --code-commit $HEAD
```

Do not run A1 or A2 with a separate ad-hoc script. Do not open result files in the middle of the invocation.

## Mandatory runner order

The runner must:

1. verify frozen cache/manifest/spec identities;
2. verify frozen V3-B F1-F4/F5-F6 artifact identities;
3. score exact V3-B control over F1-F6;
4. prove exact V3-B score/metric equivalence at `1e-12`;
5. only if control equivalence passes, execute both A1 and A2 in the same invocation;
6. apply the frozen independent gate to each challenger;
7. write top-decile overlap diagnostics;
8. record survivors and stop.

If control equivalence fails, STOP and do not interpret A1/A2.

## Frozen gates

For each challenger independently, require all frozen rules from the spec:

Absolute:

- finite reported metrics on all F1-F6;
- positive `PR-AUC - prevalence` on all `6/6`;
- positive `Q5-Q1` on all `6/6`.

Paired versus V3-B:

- PR-AUC improvement nonnegative on at least `5/6` folds;
- median paired PR-AUC improvement `>= +0.0015`;
- q25 paired PR-AUC improvement `>=0`;
- worst paired PR-AUC improvement `>= -0.0030`;
- median paired ROC-AUC change `>= -0.0020`;
- median paired Q5-Q1 change `>=0`;
- nonnegative Q5-Q1 change on at least `4/6` folds;
- F5/F6 each PR change `>= -0.0030` and F5/F6 median PR change `>=0`.

Top-decile lift and membership overlap are diagnostics only.

Allowed challenger verdicts: `PASS` or `FAIL` only.

## Required report after run

Return all of the following:

- branch, execution HEAD, final HEAD after documentation, clean/synced state;
- full pytest result;
- exact input paths/hashes for V4-A cache/manifest and four V3-B reference artifacts;
- control-equivalence status, row count, max score diff and every max metric diff;
- per-fold F1-F6 metrics for **Control, A1 and A2**: prevalence, PR-AUC, PR delta, ROC-AUC, Q1, Q5, Q5-Q1, top-decile TP/lift;
- paired per-fold A1-vs-Control and A2-vs-Control PR, ROC, Q5-Q1 and top-decile-lift changes;
- for each challenger: PR nonnegative fold count, median/q25/worst PR improvement, median ROC change, median Q5-Q1 change, Q5-Q1 nonnegative fold count, F5/F6 paired PR values and their median;
- exact gate detail and final `PASS`/`FAIL` for A1 and A2;
- top-decile Jaccard/overlap/entrants/exits for each challenger and fold;
- survivors list;
- whether `integration_authorized_by_result` is true or false, while confirming `integration_executed=false`;
- runtime by control/A1/A2 and total runtime;
- output summary/verdict/metrics/predictions/paired/overlap/runtime SHA-256 values plus model hashes;
- cumulative historical candidate count after run (`12` if ordinals 012..014 were viewed successfully);
- explicit confirmation session `1225+` was not materialized/scored, fresh-forward remained untouched, marker remained unwritten, and no calibration/execution/PnL/paper/live/main work started.

## Documentation after successful run

Create/update:

- a dated V4-A first-pass result checkpoint;
- a V4-A first-pass result handoff;
- `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md` for ordinals `012..014`;
- `docs/CURRENT_STATUS.md`.

If both A1 and A2 PASS, documentation may state that one integration **may be designed/reviewed next**, but do not implement or execute it automatically.

Commit + push all result documentation, verify branch clean/synchronized, then STOP for ChatGPT review.

## Hard prohibitions

Do not:

- change A1/A2 formulas, lookbacks, candidate IDs, HGB parameters, folds, metrics or gates;
- run a rescue/ablation/alternate normalization after seeing results;
- inspect A1 and then redesign A2 or vice versa;
- run A1+A2 integration during this task;
- materialize/score session `1225+`;
- access post-2026-07-31 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- begin V4-B or any later V4 family;
- begin calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge.
# IDX Ranking V4-A Participation — Pre-Outcome Cache Audit Handoff

Date: 2026-08-10 (Asia/Jakarta)
Status: **LOCAL DATA PREP/AUDIT ONLY — DO NOT RUN V4-A OUTCOME SCORING**

## Goal

On the Windows local data environment, pull the current `research/idx-ranking-v2-spec-v1` branch, run the full test suite, prepare the frozen V4-A A1/A2 feature cache, then run the outcome-blind feature audit.

Do **not** execute `ranking_v4_participation_cli run`. Do not inspect V4-A PR/ROC/Q5-Q1, do not fit candidate models, and do not access session `1225+` or post-2026-07-31 fresh-forward outcomes.

## Repository preflight

From the IDX Trade repository root:

```powershell
git fetch origin
git checkout research/idx-ranking-v2-spec-v1
git pull --ff-only origin research/idx-ranking-v2-spec-v1
git status --short
$HEAD = git rev-parse HEAD
python -m pytest
```

Stop if checkout is dirty before the run, pull is not fast-forward, or pytest fails.

## Frozen local inputs

Signal panel:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Official calendar:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv`

Frozen V3-B late-development cache:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\ranking_v3_final_structure_lite_late_dev_cache.parquet`

Frozen V3-B late-development cache manifest:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\ranking_v3_final_structure_lite_late_dev_cache_manifest.json`

Frozen V4-A spec:

`docs\RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`

The implementation pins and verifies the immutable source/cache/spec identities. Do not substitute similarly named files.

## Prepare command

Use a new output directory, for example:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_prepare_20260810_001`

Run:

```powershell
python -m idx_trade.ranking_v4_participation_cli prepare `
  --panel "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet" `
  --calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" `
  --v3-cache "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\ranking_v3_final_structure_lite_late_dev_cache.parquet" `
  --v3-manifest "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\ranking_v3_final_structure_lite_late_dev_cache_manifest.json" `
  --spec "docs\RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md" `
  --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_prepare_20260810_001" `
  --code-commit $HEAD
```

Expected cache status:

`RANKING_V4_A_PARTICIPATION_CACHE_FROZEN_PRE_OUTCOME`

The manifest must report:

- `post_1224_materialized=false`;
- `outcome_metrics_computed=false`;
- `fresh_forward_accessed=false`;
- `integration_candidate_materialized=false`.

## Outcome-blind audit command

Use a second new output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_audit_20260810_001`

Run:

```powershell
python -m idx_trade.ranking_v4_participation_audit `
  --cache "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_prepare_20260810_001\ranking_v4_a_participation_prepared_cache.parquet" `
  --cache-manifest "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_prepare_20260810_001\ranking_v4_a_participation_prepared_cache_manifest.json" `
  --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_audit_20260810_001"
```

The audit intentionally reads only identity + V3 participation-context + V4-A feature columns. It must report:

- `binary_target_loaded=false`;
- `outcome_columns_loaded=false`;
- `fresh_forward_accessed=false`;
- `post_1224_materialized=false`.

## Return for review

Report back exactly:

1. final branch HEAD and clean/dirty status;
2. full pytest result;
3. prepare runtime and cache/manifest SHA-256;
4. rows, tickers, signal-session range;
5. finite rate / missing rate for all seven V4-A features;
6. any constant feature;
7. all `abs_spearman_ge_095` entries;
8. highest 10 absolute Spearman correlations involving a V4-A feature;
9. audit runtime and audit SHA-256;
10. confirmation that no V4-A candidate model was fit/scored and no outcome metrics were computed.

Stop after this report. Do not authorize or execute the atomic A1/A2 model run automatically.

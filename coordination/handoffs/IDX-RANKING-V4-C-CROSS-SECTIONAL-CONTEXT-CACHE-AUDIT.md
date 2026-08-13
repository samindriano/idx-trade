# IDX Ranking V4-C Cross-Sectional Context — Pre-Outcome Cache Audit Handoff

Date: 2026-08-10 (Asia/Jakarta)
Status: **LOCAL DATA PREP/AUDIT ONLY — DO NOT RUN V4-C OUTCOME SCORING**

## Goal

On the Windows local data environment, pull the latest `research/idx-ranking-v2-spec-v1`, run the full repository test suite, prepare the frozen V4-C cross-sectional-context cache, then run the outcome-blind feature audit.

Do **not** execute `ranking_v4_cross_sectional_context_cli run`. Do not inspect V4-C PR/ROC/Q5-Q1, do not fit candidate models, and do not access session `1225+` or post-2026-07-31 fresh-forward outcomes.

V4-C was frozen while V4-B was still pre-outcome. Do not alter V4-C based on any V4-B result that may become available later.

## Mandatory reads

1. `docs/CURRENT_STATUS.md`
2. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
3. `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_EXPERIMENT_MAP_V1.md`
4. `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md`
5. `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_REVIEW_ADDENDUM_V1.md`
6. newest V4-C implementation checkpoint
7. `src/idx_trade/research_v4_cross_sectional_context.py`
8. `src/idx_trade/ranking_v4_cross_sectional_context_prepare.py`
9. `src/idx_trade/ranking_v4_cross_sectional_context_audit.py`

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

Stop if checkout is dirty before execution, pull is not fast-forward, or pytest fails.

## Frozen local input identities

Research-store root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\`

Resolve/reuse only exact SHA-verified artifacts:

- signal-research panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official exchange calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- frozen V3-B late-development cache SHA-256: `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- frozen V3-B late-development manifest SHA-256: `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`.

Known V3-B cache directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\`

For panel/calendar, reuse exact SHA-verified paths already used in V3/V4-A/V4-B. SHA identity is authoritative.

Frozen V4-C spec:

`docs\RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md`

Frozen Git blob:

`43f222f31c7c0ea15e870d22b066aae95858c81f`

## Phase 1 — prepare outcome-independent V4-C cache

Use a new empty output directory, e.g.:

```powershell
$PREP = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_c_cross_sectional_context_prepare_20260810_001"
```

Run:

```powershell
python -m idx_trade.ranking_v4_cross_sectional_context_cli prepare `
  --panel $PANEL `
  --calendar $CALENDAR `
  --v3-cache $V3CACHE `
  --v3-manifest $V3MANIFEST `
  --spec "docs\RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md" `
  --output-dir $PREP `
  --code-commit $HEAD
```

Expected cache status:

`RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_CACHE_FROZEN_PRE_OUTCOME`

Manifest must report:

- exact frozen source/spec identities;
- exact existing V3-B columns preserved;
- exact four-feature V4-C order;
- panel physical read projected to `ticker/date/high/low/close/volume/regular_market_value`;
- `context_constructed_from_full_primary_universe=true`;
- context-date count and primary-liquid cross-section count range;
- `post_1224_materialized=false`;
- `outcome_metrics_computed=false`;
- `fresh_forward_accessed=false`;
- `integration_candidate_materialized=false`.

Do not inspect target-performance metrics during prepare.

## Phase 2 — outcome-blind feature audit

Use a second new empty directory:

```powershell
$AUDIT = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_c_cross_sectional_context_audit_20260810_001"
```

Run:

```powershell
python -m idx_trade.ranking_v4_cross_sectional_context_audit `
  --cache "$PREP\ranking_v4_c_cross_sectional_context_prepared_cache.parquet" `
  --cache-manifest "$PREP\ranking_v4_c_cross_sectional_context_prepared_cache_manifest.json" `
  --output-dir $AUDIT
```

The audit intentionally loads only identity columns, exact V3-B 33 features and four V4-C features. It must report:

- `binary_target_loaded=false`;
- `outcome_columns_loaded=false`;
- `fresh_forward_accessed=false`;
- `post_1224_materialized=false`;
- row-level and date-level Spearman diagnostics separately.

Mechanical review is required before scoring if any V4-C feature:

- is constant;
- has finite rate below 80%; or
- has absolute **date-level** Spearman `>=0.95` with another V4-C feature or an existing V3-B date-level market-context feature.

## Return for ChatGPT review

Report exactly:

1. final branch HEAD and clean/synchronized state;
2. full pytest result;
3. exact resolved input paths + verified hashes;
4. prepare runtime and cache/manifest SHA-256;
5. rows, tickers, dates and signal-session range;
6. context-date count and min/median/max primary-liquid cross-section count;
7. finite/missing rate for all four V4-C features;
8. any constant feature or finite rate below 80%;
9. every `date_level_abs_spearman_ge_095` entry;
10. highest 15 absolute **date-level** Spearman correlations involving V4-C;
11. highest 15 absolute **row-level** Spearman correlations involving V4-C;
12. audit runtime and audit SHA-256;
13. explicit confirmation that context was constructed from the full primary-liquid universe, no V4-C candidate was fitted/scored, no V4-C outcome metric was computed, session `1225+` was not materialized, and fresh-forward remained untouched.

Stop after this report. Do not authorize or execute the control+ordinal-019 outcome run automatically.
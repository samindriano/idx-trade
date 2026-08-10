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

Stop if checkout is dirty before execution, pull is not fast-forward, or pytest fails.

## Frozen local input identities

Do **not** infer an input from its filename alone. Resolve/reuse the exact previously certified local artifacts and verify SHA-256 before prepare.

Research-store root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\`

Required identities:

- signal-research panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official exchange calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- frozen V3-B late-development cache SHA-256: `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- frozen V3-B late-development manifest SHA-256: `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`.

The V3-B cache and manifest were previously produced under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\`

but SHA identity is authoritative. For the signal panel and calendar, reuse their exact paths from the prior successful V3 run if available. If not, locate candidates under the research-store root and accept only a unique SHA match. Do not guess a new path.

Set the resolved paths, for example:

```powershell
$PANEL = "<EXACT_SHA_VERIFIED_SIGNAL_PANEL>"
$CALENDAR = "<EXACT_SHA_VERIFIED_OFFICIAL_CALENDAR>"
$V3CACHE = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\ranking_v3_final_structure_lite_late_dev_cache.parquet"
$V3MANIFEST = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\ranking_v3_final_structure_lite_late_dev_cache_manifest.json"

(Get-FileHash $PANEL -Algorithm SHA256).Hash.ToLower()
(Get-FileHash $CALENDAR -Algorithm SHA256).Hash.ToLower()
(Get-FileHash $V3CACHE -Algorithm SHA256).Hash.ToLower()
(Get-FileHash $V3MANIFEST -Algorithm SHA256).Hash.ToLower()
```

Stop if any hash differs from the frozen identity above or if panel/calendar resolution is ambiguous.

Frozen V4-A spec:

`docs\RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`

The implementation also verifies these immutable identities and fails closed on mismatch.

## Phase 1 — prepare outcome-independent V4-A cache

Use a new empty output directory:

```powershell
$PREP = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_prepare_20260810_001"
```

Run:

```powershell
python -m idx_trade.ranking_v4_participation_cli prepare `
  --panel $PANEL `
  --calendar $CALENDAR `
  --v3-cache $V3CACHE `
  --v3-manifest $V3MANIFEST `
  --spec "docs\RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md" `
  --output-dir $PREP `
  --code-commit $HEAD
```

Expected cache status:

`RANKING_V4_A_PARTICIPATION_CACHE_FROZEN_PRE_OUTCOME`

The manifest must report:

- exact frozen source/spec identities;
- exact existing V3-B columns preserved;
- `post_1224_materialized=false`;
- `outcome_metrics_computed=false`;
- `fresh_forward_accessed=false`;
- `integration_candidate_materialized=false`.

Do not inspect target-performance metrics during this phase.

## Phase 2 — outcome-blind feature audit

Use a second new empty directory:

```powershell
$AUDIT = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_a_participation_audit_20260810_001"
```

Run:

```powershell
python -m idx_trade.ranking_v4_participation_audit `
  --cache "$PREP\ranking_v4_a_participation_prepared_cache.parquet" `
  --cache-manifest "$PREP\ranking_v4_a_participation_prepared_cache_manifest.json" `
  --output-dir $AUDIT
```

The audit deliberately projects only identity columns, the existing V3-B participation-context features, and the seven V4-A feature columns. It must report:

- `binary_target_loaded=false`;
- `outcome_columns_loaded=false`;
- `fresh_forward_accessed=false`;
- `post_1224_materialized=false`.

## Return for ChatGPT review

Report exactly:

1. final branch HEAD and clean/synchronized state;
2. full pytest result;
3. exact resolved paths + verified hashes for panel/calendar/V3 cache/V3 manifest;
4. prepare runtime and prepared cache/manifest SHA-256;
5. rows, tickers, signal-session range;
6. finite/missing rate for all seven V4-A features;
7. any constant feature or feature with finite rate below 80%;
8. every `abs_spearman_ge_095` entry;
9. highest 10 absolute Spearman correlations involving a V4-A feature;
10. audit runtime and audit SHA-256;
11. explicit confirmation that no V4-A candidate was fitted/scored, no V4-A outcome metrics were computed, session `1225+` was not materialized, and fresh-forward remained untouched.

Stop after this report. Do not authorize or execute the atomic control+A1+A2 outcome run automatically.

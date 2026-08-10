# Ranking V4-A Participation Cache and Outcome-Blind Audit Result

Date: 2026-08-10 (Asia/Jakarta)
Branch: `research/idx-ranking-v2-spec-v1`
Run/code HEAD: `48c6128db37ab7992404b42f8d7b240e23f4ce31`

## Decision

`RANKING_V4_A_PARTICIPATION_OUTCOME_BLIND_AUDIT_COMPLETE`

The exact V4-A prepared cache was frozen and the restricted feature audit
completed successfully. This result is **not** a model result and does not
authorize the atomic V4-A control/A1/A2 outcome run.

No V4-A candidate was fitted or scored. No V4-A performance metric was
computed. The cumulative evaluated historical candidate count remains `9` and
reserved V4-A ordinals `012`, `013`, and `014` remain unviewed.

## Preflight

- remote branch was fetched and fast-forwarded to
  `48c6128db37ab7992404b42f8d7b240e23f4ce31`;
- tree was clean and synchronized before execution;
- full repository pytest: `337 passed, 0 failed, 3 warnings, 24.78s`;
- the three warnings are the existing pandas `FutureWarning`s in
  `curated_identity.py` and `tradability_anchor_reconstruction.py`;
- no engineering correction was required.

## Frozen source identities

Research-store root:

`D:/Documents/Project/idx-trade-data-gate-20260808v/`

| Input | Exact path | SHA-256 |
|---|---|---|
| signal panel | `research_feasibility_1260_20260809/unknown_state_diagnostic_1260_20260809/model_safe_signal_research_panel_1260.parquet` | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official calendar | `research_feasibility_1260_20260809/official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| frozen V3-B cache | `ranking_v3_final_structure_lite_late_dev_prepare_20260810_001/ranking_v3_final_structure_lite_late_dev_cache.parquet` | `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d` |
| frozen V3-B manifest | `ranking_v3_final_structure_lite_late_dev_prepare_20260810_001/ranking_v3_final_structure_lite_late_dev_cache_manifest.json` | `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880` |

The frozen V4-A specification Git blob was verified as
`e32fa69596291f418ae797613da219bd0d3cf69c`.

## Prepared cache

Output directory:

`D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v4_a_participation_prepare_20260810_001/`

- status: `RANKING_V4_A_PARTICIPATION_CACHE_FROZEN_PRE_OUTCOME`;
- cache SHA-256: `a487e14625942cba849b499730113cf8d0f9b3f08e866177c79642079cef6aab`;
- manifest SHA-256: `b9f15e5363e2ea0a2f912fe31a563fc45ebf7ed4788ee524540b1cdb41d308cc`;
- rows/tickers: `286,453 / 737`;
- signal-session range: `20..1224`;
- session `1225+`: not materialized;
- exact V3-B row identity/order and feature prefix: preserved;
- duplicate `(ticker, signal_session_index)` rows: `0`;
- enum values: Structure-Lite breakout state `{-2,-1,0,1,2}` and volume
  confirmation `{0,1}` when observed;
- manifest flags: `outcome_metrics_computed=false`,
  `fresh_forward_accessed=false`, `integration_candidate_materialized=false`,
  `independent_validation_claim=false`.

The inherited V3-B cache schema retains `binary_target` and `label_status` for
lineage. The official audit projection below did not load those columns or any
other outcome column.

Prepare wall-clock runtime was approximately `181s` from the Python process
start to the prepared cache/manifest write; the prepare CLI did not emit a
native elapsed field.

## V4-A feature audit

The official audit loaded only identity columns, existing V3-B participation
context, `structure_breakout_volume_confirmed`, and the seven V4-A features.
It reported `binary_target_loaded=false` and `outcome_columns_loaded=false`.

| Feature | Rows | Finite rows | Finite rate | Missing rate |
|---|---:|---:|---:|---:|
| `v4a_range_impact_logrel20` | 286,453 | 284,831 | 99.4338% | 0.5662% |
| `v4a_close_impact_logrel20` | 286,453 | 282,381 | 98.5785% | 1.4215% |
| `v4a_high_range_impact_fraction_5` | 286,453 | 283,496 | 98.9677% | 1.0323% |
| `v4a_value_persistence_fraction_5` | 286,453 | 285,047 | 99.5092% | 0.4908% |
| `v4a_value_acceleration_log_5v20` | 286,453 | 285,047 | 99.5092% | 0.4908% |
| `v4a_signed_value_5` | 286,453 | 285,236 | 99.5751% | 0.4249% |
| `v4a_signed_value_20` | 286,453 | 285,788 | 99.7679% | 0.2321% |

- constant features: none;
- finite rate below 80%: none;
- `abs_spearman_ge_095`: none;
- mechanical review required: `false`.

Highest ten absolute Spearman correlations involving at least one V4-A
feature:

| Rank | Left | Right | Spearman |
|---:|---|---|---:|
| 1 | `v4a_value_persistence_fraction_5` | `v4a_value_acceleration_log_5v20` | `+0.8942494476` |
| 2 | `v4a_high_range_impact_fraction_5` | `v4a_value_acceleration_log_5v20` | `-0.6822844572` |
| 3 | `market_relative_log_regular_value_relative_20` | `v4a_range_impact_logrel20` | `-0.6797707613` |
| 4 | `xs_rank_log_regular_value_relative_20` | `v4a_range_impact_logrel20` | `-0.6714942236` |
| 5 | `v4a_high_range_impact_fraction_5` | `v4a_value_persistence_fraction_5` | `-0.6608729823` |
| 6 | `market_relative_relative_volume_20` | `v4a_range_impact_logrel20` | `-0.6575587605` |
| 7 | `xs_rank_relative_volume_20` | `v4a_range_impact_logrel20` | `-0.6552439384` |
| 8 | `v4a_range_impact_logrel20` | `v4a_high_range_impact_fraction_5` | `+0.6173871571` |
| 9 | `market_relative_log_regular_value_relative_20` | `v4a_value_persistence_fraction_5` | `+0.5572782971` |
| 10 | `xs_rank_log_regular_value_relative_20` | `v4a_value_persistence_fraction_5` | `+0.5545986778` |

## Audit artifact

Audit output:

`D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v4_a_participation_audit_20260810_001/ranking_v4_a_participation_outcome_blind_audit.json`

- status: `RANKING_V4_A_PARTICIPATION_OUTCOME_BLIND_AUDIT_COMPLETE`;
- audit runtime: `6.3342175s`;
- audit SHA-256: `c89a19d1cce390b4734dc1de8c2cc08994217248478fd2e8025d94e90f93d31a`;
- `outcome_metrics_computed=false`;
- `fresh_forward_accessed=false`;
- `post_1224_materialized=false`.

## Boundary and next step

The cache/data audit is complete and does not select or promote a candidate.
V4-A ordinals `012..014` remain reserved and unviewed; the next step requires
a separate authorization for the atomic control+A1+A2 outcome run. Do not
start that run automatically, do not open sessions `1225+`, and do not access
post-2026-07-31 fresh-forward outcomes.

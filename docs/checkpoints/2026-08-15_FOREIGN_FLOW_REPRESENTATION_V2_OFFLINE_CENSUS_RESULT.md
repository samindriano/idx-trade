# Foreign Flow Representation V2 — Offline Materialization/Census Result

Date: 2026-08-15 (Asia/Jakarta)
Branch: `research/idx-foreign-flow-representation-v2`
Status: `REVIEW`

## Scope and boundaries

This checkpoint records one outcome-blind offline materialization and
availability census. No provider was called, no model was fit or scored, no
H10/PR-AUC/ROC/Q5-Q1 metric was computed, and no V1 alpha, protected, or
fresh-forward outcome artifact was accessed. Free-float/effective-supply work
remains outside this lane.

The accepted historical Foreign Flow archive was intersected with the pinned
clean-V2 official calendar. The archive itself contains 1,288 verified
normalized sessions from 2021-04-01 through 2026-08-13. The pinned research
calendar contains 1,260 official sessions from 2021-04-29 through 2026-07-31;
the 28 archive sessions outside that calendar were retained in provenance but
excluded from materialization because no corresponding clean-V2 next-session
mapping exists.

## Pinned inputs

| Input | Path | SHA-256 |
|---|---|---|
| Historical Foreign Flow archive manifest | `D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1\archive_manifest.json` | `fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334` |
| Clean-V2 causal market panel | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet` | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| Official exchange calendar | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| PIT security master | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260.csv` | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |

The full panel, rather than the 292k H10/model-support subset, was used to
construct the causal primary-liquid cross-section. The archive contributed
1,106,490 rows across the 1,260 calendar sessions after boundary intersection;
22,534 rows across 28 sessions were outside the pinned calendar.

## Materialized result

Output root:
`D:\Documents\Project\idx-trade-foreign-flow-representation-v2-20260815-001`

- feature rows: **1,102,400**;
- tickers: **979**;
- feature sessions: **1,259** (`2021-04-30` through `2026-07-31`);
- flow-through range: **2021-04-29 through 2026-07-30**;
- the final calendar session has no next official session and therefore has no
  feature row;
- causal context rows: **981,939**;
- primary-liquid context rows: **348,762**, across **740** tickers;
- cross-section primary-liquid size by source session: min **0**, median
  **267.5**, max **433**;
- listing interval exclusions: **1 row / 1 ticker**, `KOCI` on `2023-10-06`;
- duplicate `(ticker, feature_session)` rows: **0**;
- infinity values: **0**;
- all 15 features satisfy exact
  `feature_session = next_official(flow_through_session)`;
- own-history percentile current-observation exclusion: verified by the frozen
  builder contract and focused regression test;
- rank/divergence finite values outside source-session primary-liquid rows: **0**.

Row availability across all 15 features:

- fully available: **318,592**;
- partial: **783,240**;
- all-missing: **568**.

Row availability by feature-session year:

| Year | Fully available | Partial | All-missing |
|---|---:|---:|---:|
| 2021 | 25,490 | 98,037 | 319 |
| 2022 | 67,856 | 127,668 | 247 |
| 2023 | 58,970 | 149,279 | 0 |
| 2024 | 55,203 | 164,967 | 1 |
| 2025 | 62,893 | 162,236 | 0 |
| 2026 | 48,180 | 81,053 | 1 |

Finite counts by feature:

| Feature | Finite rows |
|---|---:|
| `foreign_participation_1` | 981,109 |
| `foreign_participation_mean_5` | 942,516 |
| `foreign_flow_shock_1` | 963,971 |
| `foreign_flow_shock_mean_5` | 930,448 |
| `foreign_flow_shock_mean_20` | 870,581 |
| `foreign_flow_shock_percentile_120` | 899,158 |
| `xs_rank_foreign_flow_shock_1` | 347,837 |
| `xs_rank_foreign_flow_shock_mean_5` | 346,420 |
| `xs_rank_foreign_flow_shock_mean_20` | 336,691 |
| `foreign_weighted_persistence_5` | 930,448 |
| `foreign_weighted_persistence_20` | 870,581 |
| `foreign_signed_streak_10` | 1,101,832 |
| `foreign_flow_acceleration_5_20` | 870,581 |
| `foreign_flow_price_divergence_5` | 346,420 |
| `foreign_flow_price_divergence_20` | 336,691 |

Missingness is split in `missingness_diagnostics.csv` between deterministic
warm-up requirements and source-data/invalid-input gaps. Rank/divergence
non-primary rows are separately reported as not applicable. Zero foreign flow
remains a valid observation; no forward-fill or synthetic replacement was
introduced.

## Artifact hashes

The output `manifest.json` is the authoritative output manifest. Its SHA-256
is:

`4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc`

| Artifact | SHA-256 |
|---|---|
| `foreign_flow_representation_v2.parquet` | `0c2212a166115b2f5b974b93096ea06b222b7451d70fa7d58257a9bed0f7a1f0` |
| `causal_market_context.parquet` | `085d7628024c3792bd3a021320ac5377b3e869bcb4ad2e8e2e1209234fe4939d` |
| `listing_interval_exclusions.csv` | `4e130836b67fa2a53d315cec3fe0ad5ad7d559cfa9814065d75b76073e3f13b7` |
| `row_availability.csv` | `cc1a9fb527061e8d1d7a7351fcba07dad792fe66450177e832215f2beecf72c8` |
| `coverage_by_year.csv` | `daafcbf5bdf66072785cfc9d7050689095af36bc5fa15e6887b49fed168d30b6` |
| `coverage_by_source_session.csv` | `47e1cd979b4b00e5da67accef67f2adc789cb398525c361acd2d9fdc02ce7657` |
| `feature_distribution.csv` | `c82f75f4e138532474ca0416cf8e2b7e8cb06330618d7c22075cdb7c3544c425` |
| `missingness_diagnostics.csv` | `390dc5ee820ffac8163d23d0ce56012fe92dd83c665b590f4914af1ac9a8ad33` |
| `input_manifest.json` | `93e39bb9829413b71965978b39d949ea4bb59c1f4e98bf86bf4486b60b585028` |
| `audit_summary.json` | `1409a14c8173702581fc2922d3316d1896111df4c33d150c054d2e1055cde733` |

## Validation

- focused V2 + runner tests: **15 passed**;
- `git diff --check`: **passed**;
- full `python -m pytest -q`: **63 passed, 1 failed** in the unrelated
  pre-existing storage test
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.
  It reports 2 conflicts (`raw_close` and `vendor_adj_close`) while the test
  expects 1. This lane did not modify `storage.py` or that contract, so the
  failure is preserved and not silently changed here.

The runner added explicit input hash verification, calendar-boundary audit,
primary-liquid rank-scope verification, and a regression test ensuring
negative divergence is not incorrectly required to be in the `[0, 1]` rank
range. The earlier intermediate run's validator failure was an engineering
check bug only; the final artifact was revalidated with the corrected checks.

## Decision / next boundary

The offline representation census is complete and ready for ChatGPT review.
No alpha experiment, model fit, performance metric, or outcome access is
authorized by this checkpoint.

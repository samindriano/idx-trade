# Handoff: Path Risk V1 Implementation + Outcome-Blind Discovery Cache

Date: 2026-08-10 (Asia/Jakarta)
Status: **AUTHORIZED IMPLEMENTATION/PYTEST/FEATURE-PREP ONLY — NO REAL PATH-RISK OUTCOME ACCESS**

## Goal

Implement the frozen first Path Risk experiment and prepare its real discovery **feature-only** cache through signal session `984` from immutable local sources.

Stop before loading the real H10 label artifact, constructing real adverse-excursion targets, fitting PR-001, or computing any real Path Risk performance metric.

## Mandatory reads

1. `docs/CURRENT_STATUS.md`
2. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
3. `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REFIT_RUNTIME_RESULT.md`
4. `docs/checkpoints/2026-08-10_RANKING_V4_FINAL_ALPHA_REVIEW_CLOSED.md`
5. `docs/PATH_RISK_V1_SPEC.md`
6. `docs/checkpoints/2026-08-10_PATH_RISK_V1_SPEC_REVIEW_PASS.md`
7. `src/idx_trade/research_labels.py`
8. `src/idx_trade/research_features.py`
9. `src/idx_trade/research_v2_features.py`
10. `src/idx_trade/research_v3_structure_lite.py`
11. `src/idx_trade/research_v2_validation.py`

Acknowledge before execution:

- ranking alpha research is closed;
- final ranker remains exact V3-B 33-feature Structure-Lite;
- Path Risk is a separate risk target and cannot retune/re-rank the final model;
- the real H10 label artifact SHA `a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677` is **forbidden to read in this task**;
- F5/F6 Path Risk outcomes are sealed;
- post-2026-07-31 outcomes are forbidden;
- the global forward marker must remain unwritten.

## Repository preflight

```powershell
git fetch origin
git checkout research/idx-ranking-v2-spec-v1
git pull --ff-only origin research/idx-ranking-v2-spec-v1
git status --short
$HEAD = git rev-parse HEAD
$UPSTREAM = git rev-parse origin/research/idx-ranking-v2-spec-v1
python -m pytest
```

Require clean/synced branch and zero pytest failures.

Current pre-task reference is `364 passed, 0 failed, 3 warnings`; new tests will increase the count, so zero failures is authoritative rather than an exact count.

## Frozen real inputs allowed in this task

### Signal panel

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

### Official calendar

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv`

SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

### Security master

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260.csv`

SHA-256:

`9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`

Do not open or hash the real H10 labels in this task beyond using the already-recorded literal SHA in source/tests/docs.

## Required implementation

Use clear modules such as:

- `src/idx_trade/path_risk_v1.py` — frozen constants, target primitive, q75 model, baseline, metrics/gate helpers;
- `src/idx_trade/path_risk_v1_prepare.py` — outcome-blind discovery feature cache/manifest/audit/CLI;
- `tests/test_path_risk_v1.py` and/or focused prepare tests.

Naming may differ if there is a strong repo-consistency reason, but semantics must remain exact.

### A. Target primitive — synthetic tests only in this task

Implement the frozen target from `docs/PATH_RISK_V1_SPEC.md`:

```text
adverse_excursion_r = max(0, (signal_reference_close - min_future_low_to_tau) / stop_distance)
```

where `tau` is the first frozen H10 barrier-touch date, else t+10.

The implementation should be able to consume a frozen H10 label frame later, but **do not call it on the real label artifact now**.

Synthetic/adversarial tests must cover at least:

- TP_FIRST with target <1;
- SL_FIRST with target >=1;
- AMBIGUOUS_SAME_BAR with target >=1;
- NO_BARRIER_HIT with target <1;
- favorable-only path -> target 0;
- missing/incomplete future session -> rejected/unresolved;
- status/barrier identity mismatch -> hard fail;
- duplicate ticker/date -> hard fail;
- no Open dependency.

### B. Frozen q75 model/evaluator

Implement exactly:

- exact final V3-B 33 feature columns;
- median SimpleImputer, add_indicator=True, keep_empty_features=True;
- no scaler;
- HistGradientBoostingRegressor loss=`quantile`, quantile=`0.75`;
- learning_rate=`0.05`;
- max_iter=`200`;
- max_leaf_nodes=`31`;
- l2_regularization=`1.0`;
- random_state=`42`.

Implement the constant training-q75 comparator and exact frozen discovery metrics/gate with synthetic tests only.

Do not change thresholds after implementing them.

### C. Outcome-blind full-primary-liquid discovery feature cache

Build features from the real panel/calendar/security master, but no labels.

Required semantics:

1. physically bound raw panel/features to signal session `<=984`;
2. use the existing causal baseline feature builder;
3. use existing V2 feature semantics so ranks/market context are based on the full same-date causal primary-liquid universe;
4. compute exact existing Structure-Lite features through `984`;
5. join by `(ticker,date)` with no orphan/duplicate rows;
6. retain **all primary-liquid rows**, not binary-label-resolved rows;
7. preserve exactly the frozen 33 model feature columns and their order;
8. include only identity columns necessary for future fold/target joining, such as `ticker`, `date`, `signal_session_index`, `universe_primary_liquid`, plus the 33 features;
9. include no label/target/outcome field.

Exact 33-feature order hash required:

`100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`

### D. Mechanical outcome-blind audit

Audit and report without reading labels:

- rows/tickers/dates;
- first/last signal session;
- per-date primary-liquid count min/median/max;
- duplicate identity count;
- exact feature-order SHA;
- per-feature finite rows/rate;
- per-feature unique finite values;
- total infinity cells;
- constant/all-null feature names, if any;
- explicit forbidden/outcome column scan;
- source hashes;
- cache hash and manifest hash;
- runtime/profile.

Hard block if:

- any source hash mismatches;
- any session `985+` materializes;
- duplicate identity exists;
- exact 33-feature order/hash differs;
- any infinity exists;
- any outcome/label/target column appears;
- no primary-liquid rows exist;
- any feature is entirely non-finite;
- any target/H10 label file was read.

Do not prune a feature because of correlation or missingness. These are the already-frozen final-ranker causal inputs.

## Suggested output

Use a new directory, e.g.:

`D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_prepare_20260810_001`

Write at least:

- `path_risk_v1_discovery_feature_cache.parquet`;
- `path_risk_v1_discovery_feature_cache_manifest.json`;
- `path_risk_v1_discovery_feature_audit.json`.

Manifest/audit flags must include:

- `status=PATH_RISK_V1_DISCOVERY_FEATURE_CACHE_FROZEN_PRE_OUTCOME`;
- `real_h10_labels_loaded=false`;
- `real_path_risk_target_computed=false`;
- `pr001_model_fitted=false`;
- `path_risk_performance_metrics_computed=false`;
- `f5_f6_path_risk_accessed=false`;
- `fresh_forward_accessed=false`;
- `forward_marker_written=false`.

## Documentation after successful prepare

Create/update:

- `docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_CACHE_AUDIT_RESULT.md`;
- `coordination/handoffs/IDX-PATH-RISK-V1-DISCOVERY-CACHE-AUDIT-RESULT.md`;
- `docs/CURRENT_STATUS.md`;
- `docs/PROJECT_LEDGER.md`.

Do not mark PR-001 as viewed. No Path Risk outcome has been accessed.

Commit/push code/tests/docs. Do not commit local data/cache artifacts.

## HARD STOP

After implementation + full pytest + real feature-only cache/audit, stop.

Do **not**:

- read the real H10 label parquet;
- compute the real adverse-excursion target;
- run PR-001 on F1-F4;
- calculate real pinball/Spearman/risk-quintile metrics;
- access Path Risk F5/F6 outcomes;
- inspect post-2026-07-31 outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- change the ranker;
- create a V4 rescue;
- create a risk-veto/integration rule;
- calibrate probabilities;
- start Stage 6 / `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge.

## Return to ChatGPT

Return:

1. branch/final HEAD/upstream/clean state;
2. full pytest result;
3. files implemented;
4. exact source/spec/feature-order identities;
5. cache rows/tickers/dates/session range;
6. primary-liquid count min/median/max;
7. per-feature finite rates and any constant/all-null findings;
8. cache/manifest/audit SHA-256;
9. runtime/profile;
10. explicit confirmation that real H10 labels were never loaded, PR-001 was not fitted, zero real Path Risk outcome/performance metrics were viewed, F5/F6 and fresh-forward remained untouched, and the global marker remains unwritten.

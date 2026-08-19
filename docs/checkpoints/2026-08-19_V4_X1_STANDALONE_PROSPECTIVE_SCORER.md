# V4-X1 Standalone Prospective Scorer

Date: 2026-08-19 (Asia/Jakarta)

Branch: `integration/v4-x1-prospective-score-v1`

Status: `IMPLEMENTED_PENDING_LOCAL_VALIDATION_AND_FIRST_SCORE`

## Scope

This checkpoint covers only the first operational step after the V4-X1 readiness lane: a standalone, immutable, outcome-blind prospective scorer for the frozen V4-X1 bundle.

It does **not** integrate scoring into the Windows EOD scheduler, does not open the outcome vault, does not fit or retune a model, does not change V4-X1 science, and does not start portfolio construction.

## Frozen identity

Generation / registry model ID:

`V4_X1_GEOMETRY3_PROSPECTIVE`

Frozen model-bundle manifest SHA-256:

`3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`

Conservative model-freeze observed-by timestamp:

`2026-08-19T14:37:16+07:00`

Exact four model files remain:

- `v4_x1_control_h5_final.joblib`
- `v4_x1_control_h10_final.joblib`
- `v4_x1_challenger_h5_final.joblib`
- `v4_x1_challenger_h10_final.joblib`

The scorer verifies each model hash against the frozen final-refit manifest before any prediction.

## Scientific-code pinning

The integration branch now carries the exact V4 scientific source required for inference, copied byte-for-byte from the frozen research parent:

- `src/idx_trade/ranking_v4_3_features.py`
  - Git blob: `59ad05f815870ae00480dc7945fe18371d8eff9c`
- `src/idx_trade/ranking_v4_3_preregistration.py`
  - Git blob: `cc1308feb51bbed16606bf7bded1ca0111644326`

The scorer checks these blobs at runtime. A science-file change therefore fails closed rather than silently changing prospective feature semantics.

Frozen representation:

- CONTROL = exact 25 V4 control features;
- CHALLENGER = the same 25 plus exact Geometry3:
  - `session_open_position_range`
  - `session_body_signed_range`
  - `session_log_high_low_range`.

The final-refit log is hash-verified and must state the same feature order for CONTROL/CHALLENGER × H5/H10.

## Fresh-session gate

A session is eligible only when both are strictly after the model freeze:

1. canonical session EOD availability at 18:00 Asia/Jakarta; and
2. actual canonical `DATA_READY.completed_at`.

Therefore late captures of 2026-08-13, 2026-08-14, and 2026-08-18 remain continuity/backfill evidence and cannot become clean X1 prospective sessions.

The scorer preserves chronological order. It selects the earliest genuinely fresh session that has not already completed for the exact frozen model fingerprint. An explicit `--session-date` must equal that next clean session or the run fails closed.

As of the canonical EOD recovery completed on 2026-08-19, the expected first candidate is **2026-08-19**, but this checkpoint does not claim it as X1 #1 until the readiness script and standalone score smoke actually pass locally.

## Causal input construction

The scorer uses:

- the existing frozen model-safe historical signal panel as causal history;
- canonical `DATA_READY` forward `model_input.parquet` snapshots after the historical panel;
- their verified sibling `session_ohlcv.parquet` artifacts for Open/Geometry3;
- local official-session calendar artifacts only;
- the canonical PIT security master.

Every required forward session from the historical panel end through the scoring date must be `DATA_READY`. Snapshot SHA, session identity, and OHLCV-vs-model-input parity are verified before feature materialization.

No provider/calendar-extension call is authorized from this scorer.

## Scoring semantics

All four frozen models are loaded without fitting:

- control H5;
- control H10;
- challenger H5;
- challenger H10.

For each head:

1. frozen point prediction is generated;
2. raw predictions are converted to the exact frozen within-date normalized percentile rank on `[0, 1]`;
3. H5/H10 consensus is fixed at `0.5 × H5 + 0.5 × H10`.

The immutable score artifact includes both control and challenger scores so the control comparison is committed prospectively before any later outcome evaluation.

Primary X1 fields are:

- `alpha_h5`
- `alpha_h10`
- `alpha_consensus`
- `rank_consensus`

Control reference fields are stored separately in the same immutable artifact.

## Artifact / registry contract

Canonical output root:

`forward_monitoring/model_runs/<session>/v4_x1_geometry3_prospective/`

Files:

- `score_artifact.parquet`
- `manifest.json`

Registry identity:

- `model_id = V4_X1_GEOMETRY3_PROSPECTIVE`
- `generation = V4-X1`
- `model_fingerprint = frozen model-bundle MANIFEST SHA-256`.

Both files use exclusive immutable publication. A completed registry row is accepted on rerun only after its artifact and manifest hashes verify; it is not rewritten.

The score manifest records exact model hashes, feature orders, scientific Git blobs, historical panel/security-master/calendar hashes, forward-history snapshot/OHLCV hashes, freshness evidence, row count, and PIT diagnostics.

Hard guard fields remain false:

- `provider_calls`
- `protected_outcome_accessed`
- `realized_forward_outcome_loaded`
- `historical_prediction_generated`
- `model_refit`
- `model_retuned`
- `science_changed`.

## Implementation

New files:

- `src/idx_trade/v4_x1_forward_score.py`
- `scripts/run_v4_x1_forward_score.py`
- `tests/test_v4_x1_forward_score_contract.py`

Frozen research modules promoted unchanged for inference:

- `src/idx_trade/ranking_v4_3_features.py`
- `src/idx_trade/ranking_v4_3_preregistration.py`

Existing readiness script remains the independent pre-score audit:

`scripts/run_v4_x1_forward_readiness.py`

## Required local validation

Do not claim first-score success until these commands pass in the exact branch checkout.

```powershell
python -m pytest -q `
  tests/test_v4_x1_forward_readiness_contract.py `
  tests/test_v4_x1_forward_score_contract.py

git diff --check
```

Then run readiness against the actual external runtime and frozen model bundle:

```powershell
python scripts/run_v4_x1_forward_readiness.py `
  --runtime-root "D:\Documents\Project\idx-trade-data-gate-20260808v" `
  --x1-model-root "D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1"
```

Required status before scoring:

`V4_X1_FORWARD_READYNESS_PASS_FIRST_SCORE_SESSION_IDENTIFIED`

Expected candidate, subject to actual readiness output:

`2026-08-19`

Only after that PASS:

```powershell
python scripts/run_v4_x1_forward_score.py `
  --runtime-root "D:\Documents\Project\idx-trade-data-gate-20260808v" `
  --x1-model-root "D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1" `
  --session-date "2026-08-19"
```

A second identical invocation must return a verified already-done result without rewriting the score artifact.

## Stop boundary

After one standalone session has been scored and idempotency verified, stop for review.

Do **not** yet:

- modify `IDXTrade-ForwardEOD` to call this scorer;
- score later sessions automatically;
- open or materialize H5/H10 outcomes;
- evaluate IC, returns, hit rate, portfolio performance, or any other outcome metric;
- alter model bytes or feature science;
- start V4-X2;
- start portfolio optimization.

Scheduler integration is a separate next step after standalone acceptance.

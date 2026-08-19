# V4-X1 Standalone Prospective Scorer

Date: 2026-08-19 (Asia/Jakarta)

Branch: `integration/v4-x1-prospective-score-v1`

Status: `PATCHED_PENDING_LOCAL_REVALIDATION_AND_FIRST_SCORE`

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

The integration branch carries the exact V4 scientific source required for inference, copied byte-for-byte from the frozen research parent:

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

The expected first candidate remains **2026-08-19**, but it is not claimed as X1 #1 until the patched readiness audit and standalone score both pass locally.

## Causal input construction

The scorer uses:

- the existing frozen model-safe historical signal panel as causal history;
- canonical `DATA_READY` forward `model_input.parquet` snapshots after the historical panel;
- the candidate session's immutable `session_ohlcv.parquet` only for Open/Geometry3;
- local official-session calendar artifacts only;
- the canonical PIT security master.

Every required forward session from the historical panel end through the scoring date must be `DATA_READY`. For every history session, snapshot SHA and session identity are verified before feature materialization.

Only the genuinely fresh candidate must also have a sibling `session_ohlcv.parquet`, and that candidate OHLCV must match the canonical model-input H/L/C/V exactly before Geometry3 is built.

Legacy Open enrichments on older forward-history sessions are deliberately **not** required for X1 history. They are not inputs to the V4 control feature state. A later provider retrieval may revise volume while preserving H/L/C, and the existing Open-enrichment contract explicitly permits that legacy case without rewriting the frozen `model_input.parquet`.

No provider/calendar-extension call is authorized from this scorer.

## 2026-08-19 local validation finding and remediation

Initial focused contract validation on commit `cb182e092ce33f2c30a80239babf96e0a08c0916` passed 13 tests.

The first real readiness run then stopped before scoring with:

`ValueError: session OHLCV volume disagrees with model input`

This exposed an integration-contract bug, not a model/science failure. The readiness/scorer implementation was incorrectly requiring sibling OHLCV parity for **all** forward-history sessions. Some older sessions have immutable legacy Open enrichments produced after the original canonical `DATA_READY` snapshot; their volume may differ by design, while their Open artifact is not used by V4-X1 historical feature construction.

Remediation:

- forward-history sessions: require canonical `DATA_READY` snapshot/hash/date only;
- fresh candidate session: require immutable sibling OHLCV and exact H/L/C/V parity;
- Geometry3 still comes only from the candidate's verified Open/H/L/C;
- freshness, chronological ordering, model hashes, science blobs, provider/outcome/refit guards are unchanged;
- no historical or protected outcome was accessed;
- no score was generated by the failed readiness run;
- no registry mutation was performed by readiness.

This changes integration validation plumbing only. Frozen V4-X1 model bytes, feature formulas, feature order, target contract, consensus formula, and prospective boundary are unchanged.

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

The score manifest records exact model hashes, feature orders, scientific Git blobs, historical panel/security-master/calendar hashes, canonical forward-history snapshot hashes, candidate snapshot/OHLCV hashes, freshness evidence, row count, and PIT diagnostics.

Hard guard fields remain false:

- `provider_calls`
- `protected_outcome_accessed`
- `realized_forward_outcome_loaded`
- `historical_prediction_generated`
- `model_refit`
- `model_retuned`
- `science_changed`.

## Implementation

Relevant files:

- `src/idx_trade/v4_x1_forward_score.py`
- `scripts/run_v4_x1_forward_score.py`
- `scripts/run_v4_x1_forward_readiness.py`
- `tests/test_v4_x1_forward_score_contract.py`
- `tests/test_v4_x1_forward_readiness_contract.py`

Frozen research modules promoted unchanged for inference:

- `src/idx_trade/ranking_v4_3_features.py`
- `src/idx_trade/ranking_v4_3_preregistration.py`

## Required local revalidation

Do not claim first-score success until these commands pass on the latest branch head:

```powershell
python -m pytest -q `
  tests/test_v4_x1_forward_readiness_contract.py `
  tests/test_v4_x1_forward_score_contract.py

git diff --check
git status --short
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

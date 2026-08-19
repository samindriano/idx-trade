# V4-X1 backfill freshness hardening

Date: 2026-08-19 Asia/Jakarta
Branch: `integration/v4-x1-prospective-score-v1`
Status: `CODE_PREPARED_LOCAL_VALIDATION_PENDING`

## Trigger

The canonical forward archive currently contains V2 score artifacts only through 2026-08-12. Repairing the existing EOD automation may therefore backfill older official sessions after the V4-X1 model-freeze timestamp (`2026-08-19T14:37:16+07:00`).

The previous readiness implementation identified post-freeze candidates using only registry `completed_at > observed_by`. That is insufficient when an old session is acquired late: a 2026-08-13/14/18 backfill completed on 2026-08-19 evening would have a post-freeze `completed_at` despite the market session itself predating model freeze.

## Hardening

`run_v4_x1_forward_readiness.py` now requires both:

1. the official session's conservative canonical EOD availability (`18:00 Asia/Jakarta` on its session date, matching the existing canonical EOD runner capture hour) to be strictly after model freeze; and
2. the actual canonical `DATA_READY.completed_at` to be strictly after model freeze.

Older sessions repaired after freeze are reported under `ignored_post_freeze_backfills` with reason `SESSION_EOD_PREDATES_MODEL_FREEZE`. They remain valid causal history for rolling-feature reconstruction but can never become X1 score session #1.

For the 2026-08-19 freeze at 14:37 WIB, this means an Aug-19 canonical EOD session can still become the first fresh X1 session after its normal EOD capture, while Aug-13/14/18 catch-up rows cannot.

## Boundary

This is an outcome-blind engineering correctness fix. It does not alter model features, fits, targets, thresholds, prospective evaluation gates, historical performance, or outcome access. No provider call is made by the readiness script.

The existing canonical `IDXTrade-ForwardEOD` catch-up remains the only authorized mechanism to repair missing historical forward sessions. Existing V2 artifacts must be preserved; do not restart the forward archive from zero.

Required local validation:

- `python -m pytest -q tests/test_v4_x1_forward_readiness_contract.py`
- `python -m py_compile scripts/run_v4_x1_forward_readiness.py`
- rerun readiness after canonical catch-up and confirm any late pre-freeze backfills appear only in `ignored_post_freeze_backfills`.
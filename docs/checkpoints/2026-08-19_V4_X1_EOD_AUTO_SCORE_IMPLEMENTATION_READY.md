# V4-X1 EOD Auto-Score — Implementation Ready

Date: 2026-08-19 (Asia/Jakarta)

Branch: `integration/v4-x1-eod-auto-score-v1`

Status: `IMPLEMENTED_PENDING_LOCAL_VALIDATION_AND_DEPLOYMENT`

This checkpoint supplements `2026-08-19_V4_X1_EOD_AUTO_SCORE_PIPELINE.md`.

Implemented boundaries:

- canonical EOD catch-up remains the sole market-data capture owner;
- before 18:00 Jakarta, AtLogOn may catch up prior closed sessions but cannot capture today's session;
- successful EOD is a hard prerequisite for downstream X1 scoring;
- new V4-X1 score commits require same-Jakarta-day session and DATA_READY completion, so late backfills are continuity-only and never retrospective prospective-counter evidence;
- the accepted frozen standalone V4-X1 scorer/science/model bundle is unchanged;
- completed X1 counter is derived only from exact frozen model-id/fingerprint DONE registry rows whose immutable score artifact and manifest hashes re-verify;
- frozen counter target remains 100; counter verification performs no outcome access;
- Windows deployment updates the existing `IDXTrade-ForwardEOD` task rather than creating another capture task;
- hardened triggers/settings are 18:30, 19:30, 20:30, AtLogOn, retry 3x/10m, StartWhenAvailable, WakeToRun, battery-safe, network guard, and IgnoreNew.

Current accepted pre-deployment state remains:

- V4-X1 clean prospective counter `1/100`;
- first clean session `2026-08-19`;
- score artifact SHA-256 `aafcea7e594dd9a0cdd8c4483a5fdfd11e75992cdb259dc8a033c51d05f32056`;
- score manifest SHA-256 `9fc47fa650b05c4fca5344cdf0ed309fd44ece5d21eb84965e8c36a59e830b9d`;
- frozen model fingerprint `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`.

No outcome, performance metric, model refit/retune, V4-X2, portfolio optimization, Path Risk, Probability, or Expected Payoff work is authorized by this checkpoint.

The currently healthy Windows scheduled task must remain untouched until:

1. focused deployment tests pass locally;
2. `git diff --check` and clean worktree pass;
3. a manual same-evening pipeline smoke verifies the already-immutable 2026-08-19 score and counter without rewriting either artifact.

Only then may the dedicated EOD runtime worktree be moved to this deployment branch and the existing Windows task be repointed with `scripts/update_forward_eod_task_v4_x1.ps1`.

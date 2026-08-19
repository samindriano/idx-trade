# V4-X1 EOD Auto-Score Deployment Pass

Date: 2026-08-19 (Asia/Jakarta)
Branch: `integration/v4-x1-eod-auto-score-v1`
Deployed pinned checkout HEAD: `deb979c782e1f8b57e0b5fca23c15088d4572e5e`
Dedicated checkout: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-v4x1-eod-auto`
Runtime root: `D:\Documents\Project\idx-trade-data-gate-20260808v`
Frozen model root: `D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1`
Scheduled Task: `IDXTrade-ForwardEOD`

## Deployment result

The existing canonical Windows Scheduled Task was repointed in-place with `Set-ScheduledTask`; no second task was created. The registered action points to `scripts\run_forward_eod_v4_x1_pipeline.ps1` in the dedicated pinned checkout and passes the canonical runtime root, frozen V4-X1 model root, and Python 3.13 executable.

The controlled `Start-ScheduledTask` deployment proof completed successfully:

- pinned deployed HEAD: `deb979c782e1f8b57e0b5fca23c15088d4572e5e`
- task state returned `Ready`
- `LastRunTime`: 2026-08-19 23:47:12 Asia/Jakarta
- `LastTaskResult`: `0`
- next scheduled run: 2026-08-20 18:30 Asia/Jakarta
- pipeline status: `PIPELINE_OK_X1_EXISTING_SCORE_VERIFIED`
- canonical EOD status: `NO_MISSING_SESSION`
- `closed_through_session`: `2026-08-19`
- `next_missing_session`: `null`
- official calendar validation: `PASS_EXACT_IDX_SESSION_CALENDAR`
- outcome access remained locked
- `provider_calls_from_x1=false`
- `protected_outcome_accessed=false`
- `model_refit=false`
- `model_retuned=false`

## V4-X1 prospective state

- completed fresh sessions: `1 / 100`
- remaining: `99`
- counted session: `2026-08-19`
- artifact verification: `PASS_ALL_DONE_ROWS`
- model ID: `V4_X1_GEOMETRY3_PROSPECTIVE`
- model fingerprint: `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`
- score artifact SHA-256: `aafcea7e594dd9a0cdd8c4483a5fdfd11e75992cdb259dc8a033c51d05f32056`
- score manifest SHA-256: `9fc47fa650b05c4fca5344cdf0ed309fd44ece5d21eb84965e8c36a59e830b9d`
- controlled scheduled-task run log SHA-256: `5fe7ae26d6a7dba0530798fbd539e33bfae64113cf025c5a58d0d4a990f563a2`

The 2026-08-19 score was verified rather than rewritten; hashes remained unchanged.

## Calendar compatibility remediation

Pre-deployment hardening exposed false failures for historical `DATA_READY` sessions whose manifests referenced the shared canonical calendar before that calendar was extended. Core session artifacts remained byte-identical. The automation path now preserves strict verification of immutable artifacts while treating the canonical shared calendar as appendable provenance for complete modern sessions. Lost legacy calendar parents remain behind the accepted immutable calendar-parent attestation contract. A strict attestation was created for 2026-08-10; canonical session bytes were not rewritten or recaptured.

## Operational verdict

`V4_X1_EOD_AUTO_SCORE_V1_DEPLOYED_CONTROLLED_TASK_RUN_PASS`

The next required evidence is ordinary live operation on the next official IDX session. No additional manual score should be created merely to advance the counter. Late historical backfills remain continuity-only and do not retroactively enter the V4-X1 fresh counter.

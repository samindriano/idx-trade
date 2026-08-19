# V4-X1 EOD Auto-Score Final Smoke PASS

Date: 2026-08-19 Asia/Jakarta

Branch: `integration/v4-x1-eod-auto-score-v1`

## Result

Controlled local Windows smoke passed after canonical-EOD hardening integration and bounded historical-calendar compatibility remediation.

Observed result:

- canonical EOD status: `NO_MISSING_SESSION`
- calendar first session: `2026-08-10`
- calendar last session: `2026-08-19`
- closed-through session: `2026-08-19`
- next missing session: `null`
- official calendar validation: `PASS_EXACT_IDX_SESSION_CALENDAR`
- outcome access: `LOCKED`
- V4-X1 pipeline status: `PIPELINE_OK_X1_EXISTING_SCORE_VERIFIED`
- process exit code: `0`
- V4-X1 counter: `1 / 100`, remaining `99`
- counter artifact verification: `PASS_ALL_DONE_ROWS`
- score session: `2026-08-19`
- score status: `V4_X1_SCORE_ALREADY_DONE_VERIFIED`
- score artifact SHA-256: `aafcea7e594dd9a0cdd8c4483a5fdfd11e75992cdb259dc8a033c51d05f32056`
- score manifest SHA-256: `9fc47fa650b05c4fca5344cdf0ed309fd44ece5d21eb84965e8c36a59e830b9d`
- frozen model fingerprint: `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`
- provider calls from X1: `false`
- protected outcome accessed: `false`
- model refit: `false`
- model retuned: `false`

Focused post-remediation regression immediately preceding the smoke passed completely (`34 passed` for compatibility/pipeline/EOD/monitoring subset).

## Historical calendar compatibility

The runtime audit showed historical canonical sessions can reference the shared official calendar at an earlier content hash. The compatibility path is bounded:

- exact current-contract sessions continue through the canonical hardening verifier first;
- modern historical sessions may tolerate only canonical shared-calendar extension while all immutable session artifacts and semantic/source/OHLCV checks remain strict;
- legacy lost-parent sessions require the accepted immutable calendar-parent attestation contract (or exact original parent bytes);
- no canonical session is rewritten or recaptured by the compatibility layer.

An immutable calendar-parent attestation was created and strictly verified for canonical session `2026-08-10` because its declared capture-time calendar bytes were unrecoverable. No provider calls or protected outcome access occurred.

## Deployment boundary

The implementation is ready for controlled Windows Scheduled Task repointing. Reuse the existing `IDXTrade-ForwardEOD` task; do not register a second canonical task. Preserve the existing task principal and verify action/triggers/settings after update. A controlled post-update invocation must pass before the task is considered deployed; the next real timer/session proof is still required before calling the lane fully automated.

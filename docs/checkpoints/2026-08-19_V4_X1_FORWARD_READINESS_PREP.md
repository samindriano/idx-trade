# V4-X1 Geometry3 — canonical forward readiness preparation

Date: 2026-08-19 (Asia/Jakarta)
Branch: `integration/v4-x1-prospective-score-v1`
Status: `V4_X1_FORWARD_READINESS_CODE_PREPARED_LOCAL_AUDIT_PENDING`

## Purpose

Prepare the outcome-blind bridge from the frozen V4-X1 four-model bundle into the existing canonical `IDXTrade-ForwardEOD` runtime without creating another EOD capture system.

Scientific parent:

- research branch `research/idx-ranking-v4-x1-prospective-eval-v1`
- final-refit PASS checkpoint commit `505e22b25d93cf6e39df66184aadcc6c3c45f527`
- external model root `D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1`
- exact model manifest SHA-256 `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`
- conservative model-freeze observed-by bound `2026-08-19T14:37:16+07:00`

## Existing runtime reused

This integration branch is based directly on `integration/forward-eod-automation-monitoring`. The existing runtime already owns canonical session capture, the SQLite `session_snapshots` registry, immutable `DATA_READY` snapshots, local forward calendar, and immutable `session_ohlcv.parquet` sidecars.

No new provider/capture/archive system is introduced.

## Readiness audit

Prepared runner:

`scripts/run_v4_x1_forward_readiness.py`

It is read-only and:

1. verifies the exact X1 final-refit manifest SHA;
2. verifies all four model-file hashes from that manifest;
3. verifies model guard flags remain outcome-clean;
4. opens the existing canonical forward registry read-only in behavior;
5. searches for the first `DATA_READY` session whose `completed_at` is strictly after the conservative model-freeze observed-by bound;
6. requires that candidate to exist in the locally certified forward calendar;
7. requires every official forward session from the historical model-safe panel end through the candidate to exist as canonical `DATA_READY` history;
8. verifies snapshot SHA and required model columns;
9. verifies the immutable same-session `session_ohlcv.parquet` against the canonical model-input snapshot;
10. does not score any model, mutate the registry, call a provider, sync/acquire a calendar, or access outcomes.

Possible bounded results:

- `V4_X1_FORWARD_READYNESS_WAITING_NO_POST_FREEZE_DATA_READY`
- `V4_X1_FORWARD_READYNESS_BLOCKED_CANONICAL_HISTORY_GAP`
- `V4_X1_FORWARD_READYNESS_PASS_FIRST_SCORE_SESSION_IDENTIFIED`

Only the PASS state authorizes implementation/execution of one immutable X1 score-only capture for the identified session. The readiness runner itself does not score.

## Current boundary

Run focused contract validation and the local readiness audit against the actual installed `IDXTrade-ForwardEOD` RuntimeRoot. If the result is WAITING, do nothing except allow the existing canonical runtime to produce its normal EOD session. If the result is BLOCKED_HISTORY_GAP, use only the existing canonical catch-up path; do not synthesize or create an X1-specific raw-data repair.

No prospective X1 outcome access is authorized.
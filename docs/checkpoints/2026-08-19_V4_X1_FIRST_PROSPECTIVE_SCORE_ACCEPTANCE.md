# V4-X1 First Prospective Score Acceptance

Date: 2026-08-19 (Asia/Jakarta)

Branch: `integration/v4-x1-prospective-score-v1`

Status: `V4_X1_FIRST_PROSPECTIVE_SCORE_ACCEPTED`

## Decision

The standalone V4-X1 prospective scorer has completed its first clean, immutable, outcome-blind score capture and passed the required idempotency replay.

The first accepted clean prospective session is:

`2026-08-19`

The V4-X1 prospective session counter is therefore:

`1 / 100`

This acceptance does not evaluate any realized H5/H10 outcome and does not authorize opening the outcome vault.

## Pre-score readiness

Latest local focused validation on branch HEAD `6002e4bd47254dc66dc369b41ac3d5bb32c57a49`:

- `tests/test_v4_x1_forward_readiness_contract.py`
- `tests/test_v4_x1_forward_score_contract.py`
- result: `16 passed`
- `git diff --check`: PASS
- worktree status: clean

Readiness status:

`V4_X1_FORWARD_READYNESS_PASS_FIRST_SCORE_SESSION_IDENTIFIED`

Readiness evidence:

- candidate session: `2026-08-19`
- candidate canonical EOD availability: `2026-08-19T18:00:00+07:00`
- candidate `DATA_READY.completed_at`: `2026-08-19T13:00:58.746235+00:00`
- candidate canonical snapshot rows: `830`
- candidate OHLCV exact H/L/C/V match: `true`
- verified required forward-history sessions: `7 / 7`
- historical panel last date: `2026-07-31`
- frozen model manifest SHA-256: `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`

Late post-freeze captures of `2026-08-13`, `2026-08-14`, and `2026-08-18` were explicitly ignored for the clean X1 prospective counter because their canonical session EOD availability predates the model freeze.

## First immutable score

First invocation returned:

`V4_X1_PROSPECTIVE_SCORE_DONE`

Identity:

- session: `2026-08-19`
- model id: `V4_X1_GEOMETRY3_PROSPECTIVE`
- model fingerprint: `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`
- scored primary-liquid rows: `290`

Canonical score artifact:

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\model_runs\2026-08-19\v4_x1_geometry3_prospective\score_artifact.parquet`

Artifact SHA-256:

`aafcea7e594dd9a0cdd8c4483a5fdfd11e75992cdb259dc8a033c51d05f32056`

Canonical score manifest:

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\model_runs\2026-08-19\v4_x1_geometry3_prospective\manifest.json`

Manifest SHA-256:

`9fc47fa650b05c4fca5344cdf0ed309fd44ece5d21eb84965e8c36a59e830b9d`

The difference between the 830-row canonical EOD snapshot and the 290-row score artifact is expected: the V4-X1 scorer emits only the frozen V4 primary-liquid scoring universe after PIT-safe feature/universe construction.

## Idempotency replay

A second identical invocation returned:

`V4_X1_SCORE_ALREADY_DONE_VERIFIED`

It verified the same immutable files and hashes:

- artifact SHA-256: `aafcea7e594dd9a0cdd8c4483a5fdfd11e75992cdb259dc8a033c51d05f32056`
- manifest SHA-256: `9fc47fa650b05c4fca5344cdf0ed309fd44ece5d21eb84965e8c36a59e830b9d`

No rewrite was required or accepted.

## Guard state

Both the scoring run and the verified replay report:

- `provider_calls = false`
- `protected_outcome_accessed = false`
- `model_refit = false`
- `model_retuned = false`

The first scoring run additionally reports:

- `realized_forward_outcome_loaded = false`

No H5/H10 realized outcome, IC, return, hit-rate, portfolio PnL, or other protected performance result was accessed or computed.

## Accepted interpretation

It is now defensible to state:

> V4-X1 prospective counter = 1/100, with first clean session 2026-08-19.

The session is clean because both canonical EOD availability and the actual canonical DATA_READY completion are strictly after the frozen model boundary, while earlier late backfills are excluded from the counter.

## Stop boundary / next lane

The standalone-scoring acceptance is complete.

Do not alter the frozen V4-X1 model/science or open outcomes.

The next separately controlled integration step may wire the already-accepted score-only runner behind successful canonical EOD completion so later genuinely fresh sessions are scored automatically and chronologically. That automation step must preserve the same freshness, immutable-artifact, idempotency, no-provider, and no-outcome guards.
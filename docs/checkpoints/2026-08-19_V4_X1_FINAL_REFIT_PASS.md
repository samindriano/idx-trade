# V4-X1 Geometry3 — final refit PASS

Date: 2026-08-19 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-x1-prospective-eval-v1`
Generation: `V4_X1_GEOMETRY3_PROSPECTIVE`
Status: `V4_X1_FINAL_REFIT_FROZEN_READY_FOR_FRESH_PROSPECTIVE_SCORING`

## Immutable local result

The preregistered V4-X1 final-refit runner completed successfully in the user's exact pinned Windows/Python environment.

External refit root:

`D:\Documents\Project\idx-v4-x1-final-refit-20260819-v1`

Manifest SHA-256:

`3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`

Final invariants:

- eligible H5 dates: `986`
- eligible H10 dates: `982`
- exact fit count: `4`
- historical prediction generated: `false`
- historical performance computed: `false`
- protected-forward accessed: `false`
- provider calls: `false`
- H5 target-support parity mismatches: `0`
- H10 target-support parity mismatches: `0`
- consensus target-support parity mismatches: `0`
- next: `START_IMMUTABLE_V4_X1_SCORE_ONLY_CAPTURE_ON_FIRST_SOURCE_CERTIFIED_OFFICIAL_SESSION_STRICTLY_AFTER_MODEL_FREEZE`

The recurrent Windows joblib/loky `wmic` physical-core warning and subprocess `cp1252` reader-thread decode exception were non-fatal. The main runner completed all four fits and emitted the successful frozen manifest above.

## Freeze-time attestation boundary

The successful result was reported in the controlling conversation at `2026-08-19T07:37:16Z` = `2026-08-19T14:37:16+07:00`. Therefore the four-model freeze was definitely complete no later than this timestamp. This conversation timestamp is recorded only as a conservative observed-by upper bound because the first version of the refit manifest did not persist a wall-clock completion timestamp.

For X1 freshness, a prospective score session is eligible only if its canonical immutable EOD/source-certification completion is strictly after `2026-08-19T14:37:16+07:00` and all other preregistered prospective gates pass. Do not infer the first eligible calendar date from this timestamp alone.

## Scientific freeze

The X1 scientific model and evaluation contract are now frozen. No further changes to features, target definitions, learner, preprocessing, hyperparameters, 80% observability rules, Top30/no-refill semantics, metric thresholds, or outcome-vault rules are authorized inside X1.

Historical V4-3R remains `V4_3R_GENERATION_NO_SURVIVOR` and is not re-evaluated under X1 rules.

No prospective outcome may be opened before `100/100` fresh score sessions are captured and H10 for score session 100 is mature.

## Runtime integration boundary

Do not create a second generic EOD capture system. V4-X1 must consume the existing canonical `IDXTrade-ForwardEOD` / forward-monitoring `DATA_READY` session archive and immutable same-session OHLCV artifacts. The next engineering step is a bounded outcome-blind runtime readiness audit and X1 score-only adapter on a separate integration branch. The canonical capture system itself is not to be duplicated or scientifically modified.
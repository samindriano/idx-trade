# Decision V2 Minimal — Implementation Result

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_TESTED_REVIEW_NO_HISTORICAL_REPLAY`

Branch: `research/idx-decision-v2-minimal-implementation-v1`

Parent preregistration: `research/idx-decision-v2-minimal-prereg-v1`

## Result

The frozen Decision V2 Minimal preregistration has been implemented without historical replay.

Implemented components:

- generic rank/state Decision V2 Minimal engine;
- separate V4-X1 verified-score adapter/profile;
- deterministic incumbent/challenger state observations;
- previous-session entry confirmation;
- two-observation exit confirmation;
- immediate universe exit;
- qualified vacancy fill with temporary underfill;
- qualified gap-5 soft replacement;
- deterministic row-order-independent output;
- adversarial/unit tests covering the frozen semantics.

## Validation

Draft PR: `#41` — `Implement Decision V2 minimal state machine`.

Code HEAD validated by GitHub Actions: `905cdc9aefe0c8949693de5dbd3d3efdea9ea786`.

Full repository pytest result:

- `427 passed`;
- `26 warnings`;
- `0 failed`.

The warnings are pre-existing pandas/NumPy deprecation/future warnings in unrelated modules/tests.

## Scientific boundary

No exact 600-OOS Decision V2 replay has been run.

No realized returns or PnL were loaded or computed. No H5/H10 rescue rule, score/rank smoothing, parameter change, alpha/model refit/retune, provider/network call, or protected/fresh-forward outcome access occurred.

The implementation remains locked to the preregistered V4-X1 profile:

- target max `10`;
- strong/entry zone `<=10`;
- retention zone `<=20`;
- previous-session entry confirmation `<=20`;
- two consecutive available observations outside `20` required for confirmed exit;
- soft replacement gap `>=5`;
- immediate universe absence exit;
- temporary underfill allowed.

## Next boundary

Before any historical replay, review PR #41 against the frozen preregistration. If accepted, the next separately gated action is an outcome-blind exact 600-OOS structural replay using the already pinned source manifest/score hashes and the preregistered mechanical acceptance gates.

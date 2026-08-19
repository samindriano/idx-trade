# V4-X1 Geometry3 — prospective preregistration and final-refit preparation

Date: 2026-08-19 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-x1-prospective-eval-v1`
Generation: `V4_X1_GEOMETRY3_PROSPECTIVE`
Status: `V4_X1_PREREG_AND_REFIT_CODE_PREPARED_LOCAL_VALIDATION_REQUIRED`

## Scientific parent

V4-X1 is a separately named prospective confirmation generation descended from the consumed V4-3R CA80 historical-development run.

Parent facts remain immutable:

- V4-3R verdict: `V4_3R_GENERATION_NO_SURVIVOR`.
- V4-3R result manifest SHA-256: `05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef`.
- V4-3R completed 24/24 fits.
- H5/H10/consensus target-support parity mismatches were all zero.
- protected-forward access was false and provider calls were zero.
- V4-3R must not be rerun or reinterpreted under X1 rules.

The reason Geometry3 is carried forward is explicitly post-selection: the consumed V4-3R result showed robust positive incremental rank-IC evidence, while the full V4-3R promotion contract failed because fixed Top30/Bottom30 portfolio metrics remained under-observed. This selection fact is disclosed rather than hidden.

## X1 model freeze

X1 does not search for another model. The scientific model architecture is frozen:

- Control: `V4_CONTROL_CONTEXT25_HGBR`.
- Challenger: `V4_CHALLENGER_SESSION_GEOMETRY3`.
- Control features: exact inherited 25.
- Challenger: exact same 25 plus the existing three completed-session Geometry3 features.
- Targets: exact inherited H5 and H10 `Close_(t+h) / Open_(t+1) - 1` definitions.
- Prediction transform: inherited within-date normalized rank.
- Consensus: 50% H5 + 50% H10.
- Decision universe: `V4_PRIMARY_LIQUID_CAUSAL_V1`.
- Learner/preprocessing/hyperparameters: unchanged inherited HGBR contract.
- No hyperparameter search, feature search, subset search, target change, or learner change.

## X1 observability policy

The only intentional evaluation-design change is a mechanically consistent 80% observability policy:

- date target coverage >= 80%;
- Top30 observable >= 24/30;
- Bottom30 observable >= 24/30;
- no refill;
- Top/Bottom identities fixed before target observability is inspected;
- exact prospective window = 100 official score sessions;
- each primary metric needs >= 80/100 admitted dates;
- robustness = five consecutive 20-session blocks;
- a block needs >= 16/20 admitted IC dates;
- at least 4/5 robustness blocks must be valid.

The values `24`, `80`, `16`, and `4` are derived mechanically from the 80% support policy. They were not chosen by searching the consumed V4-3R Top30 admitted-date counts for a passing threshold.

Top K remains 30. Metric definitions remain inherited. Portfolio gates are not removed.

## Confirmation gates

The magnitude thresholds are frozen before prospective outcome access. Consensus still requires positive rank signal, bootstrap lower bound above zero, robustness, Top30 realized percentile, and Top30-minus-Bottom30 spread. Geometry3 must also beat Control on the frozen incremental IC and portfolio thresholds. All gates are required.

Final X1 verdict is binary:

- `V4_X1_GEOMETRY3_PROSPECTIVE_CONFIRMED`; or
- `V4_X1_GEOMETRY3_NOT_CONFIRMED`.

Passing X1 would be prospective model confirmation, not automatic live-trading authorization.

## Final refit rule

Before any X1 score capture, one final refit is prepared using the already-consumed historical target corpus strictly for training:

- use all CA80 H5-eligible historical signal dates through the frozen V4-3R end;
- use all CA80 H10-eligible historical signal dates through the frozen V4-3R end;
- expected eligible dates are H5 `986`, H10 `982`;
- exact row-level target observability remains fail-closed;
- fit exactly four models: Control H5, Control H10, Challenger H5, Challenger H10;
- historical prediction generation is prohibited;
- historical performance recomputation is prohibited;
- protected-forward outcome access is prohibited;
- provider/network acquisition is prohibited.

The runner verifies the exact V4-3R selection manifest, the manifest-pinned parent summary hash, the prefit CA80 artifacts, target-support parity, runtime, parent combined replay, frozen market inputs, validation-fold identity, and pinned Git blobs before fitting.

A successful refit writes immutable joblib model bytes and a hash manifest. No prospective score is eligible before that successful manifest exists.

## Prospective boundary

X1 evaluation is genuinely fresh:

- historical V4-3R validation sessions are forbidden from X1 evaluation;
- any forward session before the successful X1 final-model manifest is frozen is forbidden from X1 evaluation;
- the first eligible score date must be the first source-certified official IDX session strictly after the successful model freeze; its date must not be inferred;
- each score is captured at EOD before future target observability is known;
- all 100 score sessions are stored outcome-blind;
- no interim outcome peeking or tuning;
- the outcome vault may open only after 100/100 score sessions exist and H10 for session 100 is mature under official-session semantics.

Once the first eligible X1 prospective score is captured, model bytes and evaluation contract are immutable. Any scientific change requires a new generation (for example V4-X2), not an X1 rescue.

## Prepared implementation

- `config/ranking_v4_x1_prospective_preregistration_v1.json`
- `src/idx_trade/ranking_v4_x1_eval.py`
- `src/idx_trade/ranking_v4_x1_decision.py`
- `config/ranking_v4_x1_final_refit_v1.json`
- `scripts/run_v4_x1_final_refit_freeze.py`
- `tests/test_ranking_v4_x1_eval.py`
- `tests/test_ranking_v4_x1_decision.py`
- `tests/test_v4_x1_final_refit_contract.py`

## Required local validation before refit

Run focused X1 tests plus compile checks in the exact pinned Python environment. Do not execute the final-refit runner if these checks fail.

After tests pass, execute the final-refit runner once against the exact immutable V4-3R external roots. Expected successful invariants:

- fit count = 4;
- eligible dates H5/H10 = 986/982;
- H5/H10/consensus target-support parity mismatches = 0/0/0;
- historical prediction generated = false;
- historical performance computed = false;
- protected-forward accessed = false;
- provider calls = false;
- final status `V4_X1_FINAL_REFIT_FROZEN_READY_FOR_FRESH_PROSPECTIVE_SCORING`.

## Coordination note

The canonical `main:coordination/TEAM_STATUS.md` inspected before this lane was stale at `Last coordinated update: 2026-08-16 00:08 Asia/Jakarta` and did not contain V4-3R or any V4-X lane. No `V4-X*` branch existed when X1 was claimed. Because the canonical ledger is a very large shared file and the available contents write is full-file replacement, this branch checkpoint records the ownership boundary rather than risking an unsafe overwrite of the stale shared ledger. A small safe canonical coordination sync remains pending when an append/surgical update path is available.

## Current boundary

`V4_X1_PREREG_AND_REFIT_CODE_PREPARED_LOCAL_VALIDATION_REQUIRED`

Do not start X1 prospective score capture until the exact final-refit manifest has successfully frozen the four model files.

# V4-X1 Clean Phase-B Final Refit — Prepared

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1`

## Status

`V4_X1_CLEAN_PHASE_B_FINAL_REFIT_PREPARED_EXECUTION_NOT_AUTHORIZED`

This checkpoint records a prepared, non-executing Phase-B clean final-refit implementation after accepted Phase A. No model has been fit in this lane.

## Controlling Phase-A acceptance

- acceptance commit: `790051c1e080678986aa174814ab6ba7440eb477`
- acceptance checkpoint blob: `e4412896ab2fcdee50a18fbb6981f2bddee28dc5`
- authoritative accepted Phase-A manifest SHA-256: `f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda`
- accepted Open policy: `PRESERVE_PARENT_EXECUTABLE_OPEN_EXCEPT_ACCEPTED_STAGE_A_CANDIDATES_V1`
- accepted clean primary rows: `348,762`
- accepted clean support rows: H5 `239,648`; H10 `237,976`
- accepted eligible-date counts remain H5 `986`; H10 `982`

## Prepared implementation

Core:
- `scripts/run_v4_x1_clean_phase_b_final_refit.py`
- blob `d18e23375076ca56d4a236217a2481c6f1c62f98`

Frozen-boundary execution wrapper:
- `scripts/run_v4_x1_clean_phase_b_final_refit_freeze.py`
- blob `509a735cff8bb92e1be6ea3ff0a24724d0a62c7b`

Tests:
- `tests/test_v4_x1_clean_phase_b_final_refit.py`
- blob `7fc2d341dbcfd9cde256e697c59875437eca92bc`
- `tests/test_v4_x1_clean_phase_b_final_refit_freeze.py`
- blob `b8681b5650c7960a86062b9b15a3665b67838bdf`

Preparation config:
- `config/ranking_v4_x1_clean_phase_b_final_refit_v1.json`
- preparation blob `635c761b64dd6f7376432eada6c86c46dee5bed8`
- `phase_b_refit_execution_authorized=false`

## Scientific contract preserved

Exactly four intended fits only:
- CONTROL H5
- CONTROL H10
- CHALLENGER H5
- CHALLENGER H10

Unchanged parent scientific contract:
- CONTROL = Context25 HGBR
- CHALLENGER = Context25 + Geometry3 HGBR
- 25 / 28 features
- same target formulas
- same CA80 gate `0.80`
- same observed-bar session semantics
- same primary-liquidity feature/universe logic applied to the accepted clean panel/security master
- same HGBR learner/hyperparameters
- no hyperparameter search
- final training policy `ALL_CA80_HEAD_ELIGIBLE_DATES_THROUGH_FROZEN_V4_3R_END`

## Clean representation

The core reconstructs the accepted Phase-A clean representation instead of reusing the old `combined` model identity:

1. parent executable-Open evidence is rederived from the frozen old panel + derivative + overlay + market-state inputs;
2. accepted Stage-A Open lineage is applied exactly (`1,657` candidate rows; `1,655` admitted clean Open; `2` fail-closed); non-candidate Open value/admission parity is required;
3. clean feature table and primary-liquid model frame are built from the accepted clean panel + clean security master;
4. primary row count must remain exactly `348,762`;
5. target-support identities materialized for Phase B must exactly equal the accepted Phase-A H5/H10 support identity artifacts before model fitting proceeds.

## Numeric target boundary remediation

Preparation review found a safety issue that would exist if numeric targets were materialized for the entire clean primary frame: that frame can contain observations after the frozen historical end.

The separate execution wrapper therefore intercepts target materialization and filters decision rows **before numeric target access** to the exact frozen V4-3R validation boundary pinned by the original 600-date validation-fold artifact:

- validation-fold SHA-256 `91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915`
- exactly 600 dates
- 6 folds x 100 dates
- post-freeze decision identities are excluded before target materialization
- post-freeze numeric target access is required to remain false.

This changes no target formula or session semantics. It enforces the already frozen historical-training authorization boundary.

## Authorized only after a separate freeze

A future execution may access historical numeric targets/ranks **for training only** and fit exactly four final models. It may not:

- score any historical model;
- compute historical IC/Top30/spread/performance;
- score prospectively in the same run;
- access protected or fresh-forward outcomes;
- access numeric training targets after the frozen historical boundary;
- call providers/network;
- change CA80, target, feature, universe, session, learner, or hyperparameter semantics;
- mutate/reset the forward counter;
- mix V4-X2 session-aligned semantics;
- repair/rescue data after seeing results.

## Current boundary

Execution remains disabled in the config. Next action is independent static/pre-execution review of this preparation. If accepted, freeze a new exact config blob with `phase_b_refit_execution_authorized=true`, pin all code/input/runtime identities, provide a local execution handoff, then run local validation and exactly one four-fit refit. Any validation or runtime invariant failure must stop without patch/rerun in the same authorization.

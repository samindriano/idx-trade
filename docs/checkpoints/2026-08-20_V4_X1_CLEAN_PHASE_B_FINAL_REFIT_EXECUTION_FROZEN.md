# V4-X1 Clean Phase-B Final Refit — Execution Frozen

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1`

## Decision

`V4_X1_CLEAN_PHASE_B_FINAL_REFIT_FROZEN_LOCAL_EXECUTION_AUTHORIZED`

The Phase-B preparation has been independently reviewed at the static/scientific-contract level and is accepted for local validation followed by exactly one clean four-model final-refit execution. No Phase-B model has been fit yet.

Authorization is conditional: any local validation failure, hash/runtime/input mismatch, Phase-A support-identity mismatch, Open-lineage mismatch, frozen-target-boundary violation, or unexpected runtime invariant must stop the execution without patching or rerunning under this authorization.

## Scientific parent and accepted clean boundary

Controlling Phase-A acceptance:
- commit `790051c1e080678986aa174814ab6ba7440eb477`
- checkpoint blob `e4412896ab2fcdee50a18fbb6981f2bddee28dc5`
- accepted Phase-A manifest SHA-256 `f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda`

Accepted Phase-A clean invariants:
- CA80 unchanged at `0.80`
- H5 support rows `239,648`
- H10 support rows `237,976`
- primary rows `348,762`
- eligible dates H5 `986`
- eligible dates H10 `982`
- frozen 600 full eligible
- no eligible sessions after frozen end
- Open policy `PRESERVE_PARENT_EXECUTABLE_OPEN_EXCEPT_ACCEPTED_STAGE_A_CANDIDATES_V1`

## Exact execution implementation

Core runner:
- `scripts/run_v4_x1_clean_phase_b_final_refit.py`
- blob `d18e23375076ca56d4a236217a2481c6f1c62f98`

Frozen-target-boundary wrapper — **this is the only authorized entry point**:
- `scripts/run_v4_x1_clean_phase_b_final_refit_freeze.py`
- blob `509a735cff8bb92e1be6ea3ff0a24724d0a62c7b`

Tests:
- `tests/test_v4_x1_clean_phase_b_final_refit.py`
- blob `7fc2d341dbcfd9cde256e697c59875437eca92bc`
- `tests/test_v4_x1_clean_phase_b_final_refit_freeze.py`
- blob `792e425b0567d2b08b9acd63ed6be57babf77f1c`

Final execution config:
- `config/ranking_v4_x1_clean_phase_b_final_refit_v1.json`
- blob `11d9fe1e0955d6f1ef11cc094332065aebe521dc`
- status `V4_X1_CLEAN_PHASE_B_FINAL_REFIT_FROZEN_LOCAL_EXECUTION_AUTHORIZED`
- `phase_b_refit_execution_authorized=true`

Original parent final-refit runner remains pinned:
- `scripts/run_v4_x1_final_refit_freeze.py`
- blob `2d538c1c99fb348b87d6c268e2df821b9099d203`

## Exactly four fits

Authorized fit set only:
1. CONTROL / H5
2. CONTROL / H10
3. CHALLENGER / H5
4. CHALLENGER / H10

CONTROL remains Context25 HGBR. CHALLENGER remains Context25 + Geometry3 HGBR. No hyperparameter search or scientific model change is authorized.

## Clean representation semantics

The Phase-B runner must reconstruct exactly the accepted clean representation:
- accepted clean panel SHA `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`;
- accepted clean security master SHA `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`;
- field provenance SHA `cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`;
- parent executable-Open evidence is preserved outside the accepted 1,657 Stage-A candidate rows;
- exact Open rederivation stats must agree with accepted Phase A;
- clean primary row count must remain `348,762`;
- newly materialized H5/H10 target-support identity sets must exactly match the accepted Phase-A support CSVs before fitting starts.

The old `combined` model-frame identity is not reused as the clean model universe.

## Frozen historical numeric-target boundary

Numeric historical targets/ranks are authorized for final training only. The wrapper filters clean primary decision rows before target materialization to the original frozen historical boundary defined by:

`docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_validation_folds.csv`

SHA-256:
`91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915`

Required:
- exactly 600 dates;
- exactly 6 folds;
- exactly 100 dates per fold;
- no numeric target materialization for clean primary rows after the frozen end;
- output must record `post_freeze_numeric_target_accessed=false` and `fresh_forward_training_target_accessed=false`.

This is an access-boundary enforcement only; target formula/session semantics are unchanged.

## Runtime / other immutable inputs

Runtime manifest SHA-256:
`cf6f1b0c859dd21b1c0f377f45d62ecdc98165ff6e0975b852a85b11cfbcaac6`

Accepted execution-lock manifest SHA-256:
`1846c94a74de8132672777c96f46580d298f942d87584e12b5e99e78e83a77f3`

Parent CA combined replay manifest SHA-256:
`12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`

Other input/code hashes are frozen in the final config blob above and must be verified before fitting.

## Explicit prohibitions

The run must not:
- generate historical predictions;
- compute historical performance, IC, Top30, spread, or any selection metric;
- score the four models on any historical or prospective rows;
- access protected/fresh-forward outcomes;
- access post-freeze numeric training targets;
- call providers/network;
- mutate/reset the forward counter;
- change CA80, session semantics, feature definitions, universe/liquidity logic, target formulas, learner, or hyperparameters;
- mix V4-X2 session-aligned semantics;
- repair or rescue data after observing a failure.

## Post-run boundary

Even after a successful four-model fit, prospective scoring remains prohibited. The run must end with status:

`V4_X1_CLEAN_PHASE_B_FINAL_REFIT_COMPLETE_INDEPENDENT_REVIEW_REQUIRED`

and stop for independent review. The four model files become candidates for immutable prospective use only after that separate acceptance.

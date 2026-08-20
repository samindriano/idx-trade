# Claim — V4-X1 Clean Phase-B Final-Refit Preparation V1

Date: 2026-08-20 (Asia/Jakarta)
Status: `FROZEN_WAITING_FOR_LOCAL_EXECUTION`
Owner: `ChatGPT/V4-X1-Clean-Phase-B-Final-Refit-Prep`
Branch: `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1`
Base lineage: `research/idx-v4-x1-clean-phase-a-open-lineage-remediation-v1`

## Scope

Prepare and freeze a separate Phase-B clean final-refit contract after accepted Phase-A remediation. The frozen local execution is authorized only after the required validation passes and may fit exactly four models: CONTROL/CHALLENGER x H5/H10.

Controlling Phase-A acceptance:
- commit `790051c1e080678986aa174814ab6ba7440eb477`
- checkpoint `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PHASE_A_OPEN_LINEAGE_REMEDIATION_ACCEPTED.md`
- checkpoint blob `e4412896ab2fcdee50a18fbb6981f2bddee28dc5`
- accepted final Phase-A manifest SHA-256 `f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda`

Phase-B execution freeze:
- checkpoint `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PHASE_B_FINAL_REFIT_EXECUTION_FROZEN.md`
- checkpoint blob `93c5f14688381dc3b51c6a5218563d3ed15ed3b2`
- config `config/ranking_v4_x1_clean_phase_b_final_refit_v1.json`
- frozen config blob `11d9fe1e0955d6f1ef11cc094332065aebe521dc`
- authorized entry point `scripts/run_v4_x1_clean_phase_b_final_refit_freeze.py`
- wrapper blob `509a735cff8bb92e1be6ea3ff0a24724d0a62c7b`

## Scientific invariants

- inherited CA80 gate remains `0.80`;
- observed-bar session semantics remain unchanged; V4-X2 session alignment is excluded;
- clean panel/security master and accepted Open-lineage remediation are the only representation changes inherited from Phase A;
- target formulas, universe/liquidity rule, feature definitions, HGBR learner/hyperparameters, and final-training policy remain unchanged;
- exactly four fits; no hyperparameter search;
- historical numeric target/rank access is permitted for frozen historical training only;
- post-freeze numeric training-target access is prohibited by the frozen-boundary wrapper;
- no historical predictions or historical performance recomputation;
- no protected/fresh-forward outcome access;
- no provider/network acquisition;
- no forward-counter reset/mutation;
- no prospective scoring in the Phase-B refit run itself.

Canonical `main:coordination/TEAM_STATUS.md` was read before this lane was claimed. No duplicate `ACTIVE` owner for this exact Phase-B clean final-refit scope was present. The canonical ledger is too large to safely replace from a truncated connector read; the local execution agent must update only this lane on canonical `main` before runtime and set it to `REVIEW` after the one run.

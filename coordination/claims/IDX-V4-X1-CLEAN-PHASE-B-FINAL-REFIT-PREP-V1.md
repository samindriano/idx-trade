# Claim — V4-X1 Clean Phase-B Final-Refit Preparation V1

Date: 2026-08-20 (Asia/Jakarta)
Status: `ACTIVE`
Owner: `ChatGPT/V4-X1-Clean-Phase-B-Final-Refit-Prep`
Branch: `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1`
Base lineage: `research/idx-v4-x1-clean-phase-a-open-lineage-remediation-v1`

## Scope

Prepare and freeze a separate Phase-B clean final-refit contract after accepted Phase-A remediation. The contract must preserve the existing V4-X1 scientific semantics and, when separately authorized for local execution, fit exactly four models only: CONTROL/CHALLENGER x H5/H10.

Controlling Phase-A acceptance:
- commit `790051c1e080678986aa174814ab6ba7440eb477`
- checkpoint `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PHASE_A_OPEN_LINEAGE_REMEDIATION_ACCEPTED.md`
- checkpoint blob `e4412896ab2fcdee50a18fbb6981f2bddee28dc5`
- accepted final Phase-A manifest SHA-256 `f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda`

## Scientific invariants

- inherited CA80 gate remains `0.80`;
- observed-bar session semantics remain unchanged; V4-X2 session alignment is excluded;
- clean panel/security master and accepted Open-lineage remediation are the only representation changes inherited from Phase A;
- target formulas, universe/liquidity rule, feature definitions, HGBR learner/hyperparameters, and final-training policy remain unchanged;
- exactly four fits; no hyperparameter search;
- no historical predictions or historical performance recomputation;
- no protected/fresh-forward outcome access;
- no provider/network acquisition;
- no forward-counter reset/mutation;
- no prospective scoring in the Phase-B refit run itself.

Canonical `main:coordination/TEAM_STATUS.md` was read before this claim. No duplicate `ACTIVE` owner for this exact Phase-B clean final-refit preparation scope was present. The canonical ledger is too large to safely replace from a truncated connector read; local execution handoff must update only this lane before any future Phase-B runtime.

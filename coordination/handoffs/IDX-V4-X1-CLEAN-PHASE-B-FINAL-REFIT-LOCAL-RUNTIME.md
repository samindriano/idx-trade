# Handoff — V4-X1 Clean Phase-B Final Refit Local Runtime

Branch: `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1`
Scope: local validation + exactly one clean four-model final refit. No redesign.

## Before execution

1. Fetch/read latest `origin/main:coordination/TEAM_STATUS.md`.
2. Confirm no duplicate `ACTIVE` owner for this exact Phase-B clean final-refit execution.
3. Add/update only the canonical main row for `V4-X1 clean Phase-B final refit` to `ACTIVE`, preserving every other row.
4. Checkout the branch above and fast-forward to remote.
5. Preserve any unrelated untracked local work. If needed, use a temporary named stash including untracked files; do not delete them.
6. Worktree must be clean before validation/runtime.

## Exact frozen blobs

Verify before any model fit:

```powershell
git rev-parse HEAD:scripts/run_v4_x1_clean_phase_b_final_refit.py
git rev-parse HEAD:scripts/run_v4_x1_clean_phase_b_final_refit_freeze.py
git rev-parse HEAD:tests/test_v4_x1_clean_phase_b_final_refit.py
git rev-parse HEAD:tests/test_v4_x1_clean_phase_b_final_refit_freeze.py
git rev-parse HEAD:config/ranking_v4_x1_clean_phase_b_final_refit_v1.json
git rev-parse HEAD:docs/checkpoints/2026-08-20_V4_X1_CLEAN_PHASE_B_FINAL_REFIT_EXECUTION_FROZEN.md
```

Expected respectively:

- `d18e23375076ca56d4a236217a2481c6f1c62f98`
- `509a735cff8bb92e1be6ea3ff0a24724d0a62c7b`
- `7fc2d341dbcfd9cde256e697c59875437eca92bc`
- `792e425b0567d2b08b9acd63ed6be57babf77f1c`
- `11d9fe1e0955d6f1ef11cc094332065aebe521dc`
- resolve from current HEAD and record it; the checkpoint content must state `V4_X1_CLEAN_PHASE_B_FINAL_REFIT_FROZEN_LOCAL_EXECUTION_AUTHORIZED`.

If any of the first five differs: STOP. Do not patch or run.

## Local validation

Run exactly these validation commands before runtime:

```powershell
python -m pytest -q `
  tests/test_v4_x1_clean_phase_b_final_refit.py `
  tests/test_v4_x1_clean_phase_b_final_refit_freeze.py `
  tests/test_v4_x1_clean_phase_a_open_lineage_remediation.py `
  tests/test_v4_x1_clean_phase_a_structural_replay.py `
  tests/test_v4_x1_clean_phase_a_no_outcome_paths.py

python -m py_compile `
  scripts/run_v4_x1_clean_phase_b_final_refit.py `
  scripts/run_v4_x1_clean_phase_b_final_refit_freeze.py

git diff --check
```

If any validation fails: STOP. Do not patch and retry under this handoff.

## Required accepted Phase-A root

`D:\Documents\Project\idx-v4-x1-clean-phase-a-open-lineage-remediation-20260820-v1`

Required final Phase-A manifest SHA-256:

`f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda`

The runner must verify the Phase-A manifest and all child output hashes before fitting.

## Required roots / anchors

- execution lock manifest:
  `D:\Documents\Project\idx-v4-x1-clean-phase-a-execution-lock-20260820-v1\v4_x1_clean_phase_a_execution_lock_manifest.json`
- historical artifact root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809`
- Stage-B clean bundle root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_stage_b_final_20260820`
- Stage-A clean root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_20260820`

Resolve the following by exact SHA-256 if there are duplicate filenames/copies. Duplicate byte-identical copies with the same required SHA are acceptable; choose one deterministically and report the chosen path.

Required SHA-256:
- clean bundle manifest `561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358`
- clean panel `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- clean security master `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`
- field provenance parquet `cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`
- parent combined CA manifest `12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`
- old Open derivative parquet `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab`
- old Open overlay parquet `2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41`

Do not call any provider or reacquire data.

## Exactly one Phase-B execution

Use a new non-existing output root, e.g.:

`D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1`

Run **the frozen-boundary wrapper**, not the core runner directly:

```powershell
python scripts/run_v4_x1_clean_phase_b_final_refit_freeze.py `
  --phase-a-root "D:\Documents\Project\idx-v4-x1-clean-phase-a-open-lineage-remediation-20260820-v1" `
  --execution-lock-manifest "D:\Documents\Project\idx-v4-x1-clean-phase-a-execution-lock-20260820-v1\v4_x1_clean_phase_a_execution_lock_manifest.json" `
  --clean-bundle-manifest "<EXACT_CLEAN_BUNDLE_MANIFEST_PATH>" `
  --clean-panel "<EXACT_CLEAN_PANEL_PATH>" `
  --clean-security-master "<EXACT_CLEAN_SECURITY_MASTER_PATH>" `
  --field-provenance "<EXACT_FIELD_PROVENANCE_PARQUET_PATH>" `
  --parent-combined-replay-root "<EXACT_PARENT_CA_REPLAY_ROOT>" `
  --artifact-root "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809" `
  --open-derivative-root "<EXACT_OLD_OPEN_DERIVATIVE_ROOT>" `
  --overlay-root "<EXACT_OLD_OPEN_OVERLAY_ROOT>" `
  --output-dir "D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1"
```

There is no `--old-security-master` argument in Phase B; the clean security master is the scientific identity input. The old panel/Open derivative/overlay are used only to reconstruct the accepted parent executable-Open lineage before applying the accepted clean Open overrides.

## Fail-closed requirements before first fit

The run must stop before fitting if any of these fails:

- exact runtime/package match;
- any pinned code/input hash;
- accepted Phase-A manifest/child hashes;
- accepted Open-lineage stats / policy;
- clean primary row count exactly `348,762`;
- clean H5 target-support identity exactly `239,648` rows and exact identity match to Phase A;
- clean H10 target-support identity exactly `237,976` rows and exact identity match to Phase A;
- accepted clean training-date-count artifact unchanged;
- original 600-date / 6x100 validation-fold boundary hash unchanged;
- any post-freeze decision row is sent to numeric target materialization.

## Fit authorization

If and only if all pre-fit guards pass, fit exactly four models:

- CONTROL H5
- CONTROL H10
- CHALLENGER H5
- CHALLENGER H10

No hyperparameter search, no fifth fit, no retry after a fit failure.

## Absolutely prohibited

- historical model scoring/predictions;
- historical IC/Top30/spread/performance recomputation;
- prospective model scoring in this run;
- protected/fresh-forward outcome access;
- numeric target access after frozen historical boundary;
- provider/network calls;
- forward-counter reset/mutation;
- CA80/session/target/feature/universe/learner/hyperparameter changes;
- V4-X2 session-aligned semantics;
- repair/rescue after seeing a failure.

## Required result report

After the exactly-one run, report:

- branch + HEAD;
- canonical TEAM_STATUS coordination commit;
- focused pytest count/result;
- py_compile PASS/FAIL;
- git diff --check PASS/FAIL;
- final status;
- final manifest path + SHA-256;
- fit_count and exact four mode/head entries;
- H5/H10 eligible-date counts;
- H5/H10 Phase-A support identity exact-match flags;
- H5/H10 final training rows + dates for CONTROL and CHALLENGER;
- feature count 25/28 and exact feature-list identity checks;
- all four model file SHA-256 hashes;
- frozen target-boundary summary: rows before boundary, materialized rows, post-freeze excluded rows, frozen end session/date;
- `post_freeze_numeric_target_accessed=false`;
- `fresh_forward_training_target_accessed=false`;
- historical prediction/performance/model scoring flags all false;
- protected/fresh-forward flags false;
- provider/network false;
- forward counter mutation false;
- prospective scoring authorization false.

After the run, update only this Phase-B lane on canonical `TEAM_STATUS` to `REVIEW` and STOP. Do not score the resulting models. Independent acceptance is required next.

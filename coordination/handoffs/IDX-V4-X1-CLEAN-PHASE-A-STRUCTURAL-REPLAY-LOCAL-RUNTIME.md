# Handoff — V4-X1 Clean Phase-A Structural Replay Local Runtime

Branch: `research/idx-v4-x1-clean-phase-a-structural-replay-v1`
Scope: execution-only validation + exactly one outcome-blind Phase-A structural replay. Do not redesign methodology.

## Before execution

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md`.
2. Confirm no other `ACTIVE` owner for this exact Phase-A structural replay.
3. Claim/update only this lane on canonical `main:coordination/TEAM_STATUS.md` before runtime, preserving every other row.
4. Use a clean worktree on `research/idx-v4-x1-clean-phase-a-structural-replay-v1`.
5. Do not alter the frozen runner/config after checkout.

## Frozen implementation

- runner: `scripts/run_v4_x1_clean_phase_a_structural_replay.py`
- runner Git blob: `352e331439dd89c8d66d6b36f98997d3b667e2c0`
- config: `config/ranking_v4_x1_clean_phase_a_structural_replay_v1.json`
- config Git blob: `c1dc1706b2dfc0c68b925988a03f1cbca83070c9`
- scientific base acceptance: `30885d3a7c37511ef9cdedd6cb1f599f3350dea1`
- accepted execution-lock manifest SHA: `1846c94a74de8132672777c96f46580d298f942d87584e12b5e99e78e83a77f3`

## Local validation

Run before the replay:

```powershell
python -m pytest -q `
  tests/test_v4_x1_clean_phase_a_structural_replay.py `
  tests/test_v4_x1_clean_phase_a_no_outcome_paths.py

python -m py_compile scripts/run_v4_x1_clean_phase_a_structural_replay.py
git diff --check
```

If any validation fails: **STOP**. Do not patch and retry in the same handoff.

## Resolve exact external inputs

Use exact SHA-256, not filenames/mtime guesses.

Known roots/anchors:

- accepted execution lock:
  `D:\Documents\Project\idx-v4-x1-clean-phase-a-execution-lock-20260820-v1\v4_x1_clean_phase_a_execution_lock_manifest.json`
- Stage C root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\pit_security_identity_stage_c_v1_20260820`
- historical artifact root containing calendar/panel/anchors/intervals:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809`
- Stage-B final clean bundle root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_stage_b_final_20260820`
- Stage-A clean root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_20260820`

Required exact hashes are all in `config/ranking_v4_x1_clean_phase_a_structural_replay_v1.json`:

- old panel: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- anchors: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`
- intervals: `fd255f21a3accd763286fbd0b0c6d9d501d618ae611cc0681017e001bdba83cc`
- old Open derivative: `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab`
- old Open overlay: `2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41`
- old security master: `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240`
- clean bundle manifest: `561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358`
- clean panel: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- clean security master: `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`
- field provenance: `cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`
- Stage-C manifest: `5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61`
- parent combined CA replay manifest: `12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`

Resolve the old Open derivative root, Open overlay root, old security-master file, clean panel/security-master/provenance files, and parent combined CA replay root by those exact hashes if their filenames are not already obvious from prior runtime manifests. No provider/network calls.

## Exactly one Phase-A run

Use a new non-existing output directory, for example:

`D:\Documents\Project\idx-v4-x1-clean-phase-a-structural-replay-20260820-v1`

Then run exactly once:

```powershell
python scripts/run_v4_x1_clean_phase_a_structural_replay.py `
  --execution-lock-manifest "D:\Documents\Project\idx-v4-x1-clean-phase-a-execution-lock-20260820-v1\v4_x1_clean_phase_a_execution_lock_manifest.json" `
  --clean-bundle-manifest "<EXACT_STAGE_B_BUNDLE_MANIFEST_PATH>" `
  --clean-panel "<EXACT_CLEAN_PANEL_PATH>" `
  --clean-security-master "<EXACT_FINAL_SECURITY_MASTER_PATH>" `
  --field-provenance "<EXACT_FIELD_PROVENANCE_PARQUET_PATH>" `
  --stage-c-root "D:\Documents\Project\idx-trade-data-gate-20260808v\pit_security_identity_stage_c_v1_20260820" `
  --parent-combined-replay-root "<EXACT_PARENT_CA_REPLAY_ROOT>" `
  --artifact-root "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809" `
  --open-derivative-root "<EXACT_OLD_OPEN_DERIVATIVE_ROOT>" `
  --overlay-root "<EXACT_OLD_OPEN_OVERLAY_ROOT>" `
  --old-security-master "<EXACT_OLD_SECURITY_MASTER_PATH>" `
  --output-dir "D:\Documents\Project\idx-v4-x1-clean-phase-a-structural-replay-20260820-v1"
```

## Fail-closed rules

The first run must stop without repair if any of these occurs:

- old H5/H10 re-derivation differs by even one identity from Stage-C oracle;
- any input/code hash differs;
- clean frozen 600 dates no longer all pass inherited CA80;
- frozen tail-600 changes;
- eligible sessions appear after frozen historical end;
- any of 12 clean fold/head training sets is empty;
- runtime raises any unanticipated structural invariant.

Do not change the 0.80 gate, CA semantics, feature/session semantics, security-master policy, Open policy, universe rule, folds, or output logic after seeing the first result. Do not rerun in the same handoff after a fail-closed result.

## Required report

Report only structural/outcome-blind results:

- branch + final HEAD;
- focused pytest / py_compile / diff-check;
- replay status;
- manifest path + SHA-256;
- `old_support_oracle_exact_match`;
- clean CA80 gate PASS/FAIL and frozen minimum H5/H10/consensus rates;
- clean support H5/H10 row counts;
- H5/H10 ADD/DROP support counts;
- old vs clean primary row counts/add/drop;
- count of representation features with any exact finite-value change;
- aggregate missingness transitions;
- clean training-date counts for all 12 fold/head sets;
- all safety flags;
- canonical TEAM_STATUS coordination commit.

Do not report numeric target returns, target ranks, model scores, IC, Top30/spread performance, or any protected/fresh-forward outcome because Phase A must not access them.

After the one run, set the lane to `REVIEW` and **STOP**. Phase-B refit remains prohibited until independent review.

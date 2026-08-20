# Handoff — V4-X1 Clean Phase-A Open-Lineage Remediation Local Runtime

Branch: `research/idx-v4-x1-clean-phase-a-open-lineage-remediation-v1`
Scope: validation + exactly one outcome-blind remediation replay. Do not redesign methodology.

## Before execution

1. Fetch/read latest `origin/main:coordination/TEAM_STATUS.md`.
2. Confirm there is no duplicate `ACTIVE` owner for this exact remediation.
3. Add/update a canonical main row for `V4-X1 clean Phase-A Open-lineage remediation V1` as `ACTIVE`, preserving every other row.
4. Use a clean worktree on this branch.
5. Verify frozen blobs before running:

```powershell
git rev-parse HEAD:scripts/run_v4_x1_clean_phase_a_structural_replay.py
git rev-parse HEAD:config/ranking_v4_x1_clean_phase_a_structural_replay_v1.json
git rev-parse HEAD:scripts/run_v4_x1_clean_phase_a_open_lineage_remediation.py
git rev-parse HEAD:tests/test_v4_x1_clean_phase_a_open_lineage_remediation.py
```

Expected respectively:

- `352e331439dd89c8d66d6b36f98997d3b667e2c0`
- `c1dc1706b2dfc0c68b925988a03f1cbca83070c9`
- `91ecfd719c04fbd2749d2e1cf0d0f3bc0c2bec9a`
- `23268a37c5154895e1ed5a11ac15bb17131697f4`

If any blob differs: STOP.

## Local validation

```powershell
python -m pytest -q `
  tests/test_v4_x1_clean_phase_a_structural_replay.py `
  tests/test_v4_x1_clean_phase_a_no_outcome_paths.py `
  tests/test_v4_x1_clean_phase_a_open_lineage_remediation.py

python -m py_compile `
  scripts/run_v4_x1_clean_phase_a_structural_replay.py `
  scripts/run_v4_x1_clean_phase_a_open_lineage_remediation.py

git diff --check
```

If any validation fails: STOP. Do not patch and retry in this handoff.

## Required immutable first-run evidence

First failed replay manifest:

`D:\Documents\Project\idx-v4-x1-clean-phase-a-structural-replay-20260820-v1\MANIFEST.json`

Required SHA-256:

`1dedb76db7c1fc620e4feb286e409d0266bf367581cbf7dab28bc862f298787c`

This file must remain untouched.

## Runtime inputs

Use the exact same external inputs and paths resolved for the first Phase-A run. In particular:

- execution lock manifest:
  `D:\Documents\Project\idx-v4-x1-clean-phase-a-execution-lock-20260820-v1\v4_x1_clean_phase_a_execution_lock_manifest.json`
- Stage-C root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\pit_security_identity_stage_c_v1_20260820`
- historical artifact root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809`
- Stage-B clean bundle root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_stage_b_final_20260820`
- Stage-A clean root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_20260820`

Keep the exact resolved paths used in the successful first-run hash validation for:

- clean bundle manifest;
- clean panel;
- clean security master;
- field provenance;
- parent combined CA replay root;
- old Open derivative root;
- old Open overlay root;
- old security master.

Do not search providers or reacquire data.

## Exactly one remediation replay

Use a new, non-existing output root, e.g.:

`D:\Documents\Project\idx-v4-x1-clean-phase-a-open-lineage-remediation-20260820-v1`

Run the wrapper, not the original runner:

```powershell
python scripts/run_v4_x1_clean_phase_a_open_lineage_remediation.py `
  --failed-replay-manifest "D:\Documents\Project\idx-v4-x1-clean-phase-a-structural-replay-20260820-v1\MANIFEST.json" `
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
  --output-dir "D:\Documents\Project\idx-v4-x1-clean-phase-a-open-lineage-remediation-20260820-v1"
```

## Invariants that must be reported

The clean price-evidence summary must show:

- policy `PRESERVE_PARENT_EXECUTABLE_OPEN_EXCEPT_ACCEPTED_STAGE_A_CANDIDATES_V1`;
- candidate rows `1,657`;
- admitted rows `1,655`;
- fail-closed rows `2`;
- `non_candidate_open_value_exact_parity=true`;
- `non_candidate_open_admission_exact_parity=true`;
- market state reused exactly from parent evidence.

The original old-support oracle must still exact-match Stage C before any clean verdict is accepted.

Then report the same structural Phase-A outputs as the first run:

- final status;
- final manifest path + SHA-256;
- old-support oracle exact match;
- clean CA80 PASS/FAIL;
- frozen minimum H5/H10/consensus support rates;
- frozen-600 full eligibility;
- tail-600 identity status;
- eligible sessions after frozen end;
- H5/H10 old vs clean support rows and ADD/DROP;
- primary old/clean/add/drop/shared rows;
- number of 28 representation features with finite-value changes;
- aggregate finite→missing / missing→finite transitions;
- all 12 fold/head clean training-date counts;
- all safety flags;
- canonical TEAM_STATUS coordination commit.

## Fail-closed rule

If validation fails, input/blob hash changes, first-failed manifest hash changes, candidate population differs from `1657/1655/2`, any non-candidate Open parity invariant fails, old support no longer exact-matches Stage C, or any unexpected runtime invariant occurs: STOP. Do not patch/rerun in this handoff.

If the remediated clean CA80 still fails, record it as `REVIEW` and stop. Do not change the `0.80` gate or any CA/data/model semantics.

If it passes, also stop at `REVIEW`. Phase-B refit remains prohibited until independent review.

After the one run, update only this remediation row on canonical `TEAM_STATUS` to `REVIEW`.
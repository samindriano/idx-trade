# Handoff — V4-X1 Clean Phase-A Execution Lock Local Capture

Branch: `research/idx-v4-x1-clean-phase-a-execution-lock-v1`
Scope: execution-only local verification/capture. Do not redesign methodology.

## Required sequence

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md` and confirm no duplicate active owner for this exact clean Phase-A execution-lock scope.
2. Use a clean worktree on `research/idx-v4-x1-clean-phase-a-execution-lock-v1`.
3. Run:
   - `python -m pytest -q tests/test_v4_x1_clean_phase_a_execution_lock.py`
   - `python -m py_compile scripts/capture_v4_x1_clean_phase_a_execution_lock.py`
   - `git diff --check`
4. Resolve the local accepted artifacts by the exact SHA-256 pins in `config/ranking_v4_x1_clean_phase_a_execution_lock_v1.json`:
   - Stage-B final bundle manifest `561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358`
   - Stage-A clean panel `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
   - final security master `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`
   - field provenance parquet `cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`
   - V4-3R CA80 prefit manifest `0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc`
5. Use a new non-existing output directory, e.g. `D:\Documents\Project\idx-v4-x1-clean-phase-a-execution-lock-20260820-v1`.
6. Run exactly one hash-only capture:

```powershell
python scripts/capture_v4_x1_clean_phase_a_execution_lock.py `
  --final-bundle-manifest "<EXACT_STAGE_B_MANIFEST_PATH>" `
  --clean-panel "<EXACT_CLEAN_PANEL_PATH>" `
  --security-master "<EXACT_FINAL_SECURITY_MASTER_PATH>" `
  --field-provenance "<EXACT_FIELD_PROVENANCE_PARQUET_PATH>" `
  --ca80-prefit-manifest "<EXACT_CA80_PREFIT_MANIFEST_PATH>" `
  --output-dir "D:\Documents\Project\idx-v4-x1-clean-phase-a-execution-lock-20260820-v1"
```

7. Report:
   - branch + final HEAD;
   - focused test / py_compile / diff-check result;
   - capture status;
   - output manifest path and SHA-256;
   - exact runtime-match result;
   - all external hash-match results;
   - all safety flags.
8. Stop. Do **not** run Phase-A structural replay in the same handoff.

## Hard boundaries

No provider/network calls, no numeric target/return/rank access, no target materialization, no model fit/score, no predictions/performance, no protected/fresh-forward outcome, no counter mutation, no clean-data or CA mutation, no V4-X2/session-aligned work, no tuning/rescue.

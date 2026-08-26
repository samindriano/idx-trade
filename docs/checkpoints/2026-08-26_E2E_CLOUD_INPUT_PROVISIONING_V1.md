# E2E Paper Cloud Input Provisioning V1

Status: `BLOCKED_R2_S3_CREDENTIALS_MISSING_LOCAL`

Date: 2026-08-26 (Asia/Jakarta)

## Scope

This bounded task audited and prepared the exact private E2E Paper cloud input
bundle for accepted implementation `integration/idx-e2e-baseline-paper-v1@043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2`.
It did not merge PR #93, activate a scheduler, run an E2E phase, call an IDX
provider, access outcomes, or change model/science/counter state.

The production input manifest is not uploaded because the local process has no
S3-compatible R2 endpoint/bucket/access-key values. The existing GitHub secret
names are present, but their values are not readable from this local process;
no secret value was printed or guessed.

## Accepted local input inventory

All ten required roles were found and matched their accepted SHA-256 identity.
The production object key is the `inputs/` prefix plus the declared relative
path below. No production object was written.

| role | local path | bytes | SHA-256 | production key |
|---|---|---:|---|---|
| `execution_schedule` | `D:\\Documents\\Project\\idx-e2e-schedule-attestation-20260824-v1\\attestation\\execution_schedule_attestation.json` | 5,509 | `6c81eb8457cbb5558339e08bd7a159fe700adbe441e287f56a99fb237e081a65` | `e2e-paper-v1/inputs/schedule/execution_schedule_attestation.json` |
| `execution_schedule_source` | `D:\\Documents\\Project\\idx-e2e-schedule-attestation-20260824-v1\\attestation\\official_source.pdf` | 1,036,672 | `ca444520365cb1d8a74eed4c0e9c72c5718333e9a2745b1002bf6256c454a96e` | `e2e-paper-v1/inputs/schedule/official_source.pdf` |
| `clean_panel` | `D:\\Documents\\Project\\idx-trade-data-gate-20260808v\\v4_x_clean_data_consolidation_v1_20260820\\model_safe_signal_research_panel_1260_stage_a_clean_candidate.parquet` | 17,400,102 | `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e` | `e2e-paper-v1/inputs/panel/model_safe_signal_research_panel_1260_stage_a_clean_candidate.parquet` |
| `clean_security_master` | `D:\\Documents\\Project\\idx-trade-data-gate-20260808v\\v4_x_clean_data_consolidation_v1_stage_b_final_20260820\\final_security_master_v1.csv` | 74,625 | `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e` | `e2e-paper-v1/inputs/security_master/final_security_master_v1.csv` |
| `model_manifest` | `D:\\Documents\\Project\\idx-v4-x1-clean-phase-b-final-refit-20260820-v1\\MANIFEST.json` | 7,310 | `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf` | `e2e-paper-v1/inputs/models/MANIFEST.json` |
| `model_control_h5` | `D:\\Documents\\Project\\idx-v4-x1-clean-phase-b-final-refit-20260820-v1\\v4_x1_clean_control_h5_final.joblib` | 782,825 | `f727b10c6ea72c9ca7b447977ed4fa9cd3b5b32adb81793921c425d9085665b2` | `e2e-paper-v1/inputs/models/v4_x1_clean_control_h5_final.joblib` |
| `model_control_h10` | `D:\\Documents\\Project\\idx-v4-x1-clean-phase-b-final-refit-20260820-v1\\v4_x1_clean_control_h10_final.joblib` | 782,809 | `737be8c47fe2d689dab09950a931c1339039ed8ae379b79f0bfd5a8c2e7605db` | `e2e-paper-v1/inputs/models/v4_x1_clean_control_h10_final.joblib` |
| `model_challenger_h5` | `D:\\Documents\\Project\\idx-v4-x1-clean-phase-b-final-refit-20260820-v1\\v4_x1_clean_challenger_h5_final.joblib` | 789,593 | `d8a73d03ff72ab82826ef4e1be5e2073f6a61a5bb01b4e4268428436dc5eb082` | `e2e-paper-v1/inputs/models/v4_x1_clean_challenger_h5_final.joblib` |
| `model_challenger_h10` | `D:\\Documents\\Project\\idx-v4-x1-clean-phase-b-final-refit-20260820-v1\\v4_x1_clean_challenger_h10_final.joblib` | 789,593 | `935a6f9aeaa2ca30a4016819e3848d284eb677e38153a7bd3126da0c33a9f95d` | `e2e-paper-v1/inputs/models/v4_x1_clean_challenger_h10_final.joblib` |
| `model_fit_log` | `D:\\Documents\\Project\\idx-v4-x1-clean-phase-b-final-refit-20260820-v1\\v4_x1_clean_final_refit_log.json` | 5,205 | `e3ac7eae11cf52ac4af83c08cc01e967bd7538c4817be7b9b8e49787c319e484` | `e2e-paper-v1/inputs/models/v4_x1_clean_final_refit_log.json` |

The accepted model lineage is the clean V4-X1 Phase-B refit manifest
`30e1b505...`; the accepted clean panel and security-master identities are
`25eb0d0c...` and `51fecc3b...`, respectively, as recorded by the accepted
clean prospective deployment checkpoints.

## Offline manifest and verification

The exact current contract was used:

- schema: `idx_trade_e2e_paper_cloud_inputs_v1`;
- contract: `CLOUD_FIRST_E2E_PAPER_V1`;
- manifest key: `inputs/manifest.json` under prefix `e2e-paper-v1`;
- required roles: all ten roles listed above;
- manifest payload SHA-256: `a383f1276a52e464d89e0d90b660021a97c647e9a4a3ed46ac15bb4e3662152a`;
- prepared offline manifest SHA-256: `858327909343a887c54fbc5e3bea4dafe6f7a8b89f2422a313b954dee04c08ee`.

The offline preparation/verification root is external and remains outside Git:

`D:\\Documents\\Project\\idx-e2e-cloud-input-provisioning-20260826-v2`

Its `CloudInputBundle.load` and materialization validation passed for all ten
roles. Every child hash matched. The existing official schedule loader passed
with the co-located source document. The schedule covers `2026-01-01` through
`2026-12-31`, has 239 planned sessions and 22 holidays, excludes
`2026-08-25`, and identifies `2026-08-26` as the next planned session after
`2026-08-24`.

The offline verification record SHA-256 is
`8eac24c971e731f410363e3bddbaa6c360634d43be42e6e508b80e0cbdff66d7`.

## R2 smoke/provisioning gate

The required `ConditionalS3Store` smoke was not invoked because the local
process had none of the four required values:

- `R2_ACCOUNT_ID`;
- `R2_BUCKET_NAME`;
- `R2_ACCESS_KEY_ID`;
- `R2_SECRET_ACCESS_KEY`.

GitHub secret names were confirmed to exist through authenticated metadata, but
secret values cannot be read locally. The Cloudflare API token shown in the
operator UI is not substituted for the S3 access-key/secret-key pair expected
by `ConditionalS3Store`.

Therefore:

- throwaway R2 smoke: `NOT RUN`;
- production child uploads: `NOT RUN`;
- production write-last manifest: `NOT RUN`;
- production live readback: `NOT RUN`.

No R2 production prefix was read or changed.

## Validation

- `python -m pytest -q tests/test_e2e_paper_cloud_runtime_v1.py --basetemp D:\\Documents\\Project\\idx-e2e-cloud-input-provisioning-20260826-test-temp`: `37 passed`;
- `python -m py_compile` for the cloud runtime, cloud runner, and ConditionalS3 smoke entrypoint: `PASS`;
- `git diff --check`: `PASS` before documentation changes;
- source/worktree status: clean before documentation changes.

## Guard result

`provider_calls=false`, `model_fit=false`, `model_score=false`,
`protected_outcomes_accessed=false`, `scheduler_mutated=false`,
`production_r2_accessed=false`, `PR_93_merged=false`.

## Next action

Run the existing smoke and write the immutable production bundle only from a
process that has the four exact R2 S3 credential variables available. Do not
use the API token as a substitute, merge #93, activate the scheduler, or run a
live E2E phase until smoke and production readback pass.

Final verdict: `BLOCKED_R2_S3_CREDENTIALS_MISSING_LOCAL`

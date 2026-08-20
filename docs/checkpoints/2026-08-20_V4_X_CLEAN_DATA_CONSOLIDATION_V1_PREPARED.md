# V4-X Clean-Data Consolidation V1 — Prepared for Offline Stage-A Runtime

Date: 2026-08-20 (Asia/Jakarta)
Branch: `data/v4-x-clean-data-consolidation-v1`
Prepared HEAD: `4ebd86021e49169864f8fdf9b698363935c6358e`
Status: `STAGE_A_IMPLEMENTATION_PREPARED_LOCAL_VALIDATION_REQUIRED`

## Prepared implementation

The branch now contains:

- explicit branch claim with collision boundary against the ACTIVE PIT Security Identity / Listing-Domain Stage-C lane;
- frozen Stage-A protocol;
- machine-readable pinned config;
- `src/idx_trade/v4_x_clean_data_consolidation.py`;
- `scripts/run_v4_x_clean_data_consolidation_v1.py`;
- `tests/test_v4_x_clean_data_consolidation.py`.

The implementation starts from the immutable frozen parent panel, applies only the accepted H/L/C overlay and accepted Open remediation, explicitly makes the two unsupported Open candidate rows unavailable, and hard-fails if any other parent field changes. Volume and Regular-Market Value are separately asserted unchanged. A one-row-per-parent-row field-level provenance sidecar and small correction ledger are emitted.

## Frozen local dependencies

The runner requires the already materialized external artifacts under `D:\Documents\Project`, including:

- frozen panel SHA `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar SHA `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- H/L/C remediation manifest SHA `2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278`;
- Open remediation manifest SHA `753d5470bd240bbf6158142bc5a2b339cea96f83cfb7451c5e18fc10cf5f060f`;
- full-panel official-integrity manifest SHA `bf87e0c8ce49468113eec32cb7df931ff0df887444de727a57c65b495d87c016`;
- Regular-Market Value audit manifest SHA `e7147f9f378d8c05ed5307e9c0fd92c29a8465221207e2484001a7772c8d8f37`.

No provider access is required or allowed.

## Required local validation

Run focused tests first:

`python -m pytest -q tests/test_v4_x_clean_data_consolidation.py`

Only if focused tests pass, run:

`python scripts/run_v4_x_clean_data_consolidation_v1.py`

Expected successful status:

`STAGE_A_CONSOLIDATION_MATERIALIZED_WAITING_FOR_IDENTITY_ADJUDICATION`

The runtime must not be retried by loosening pins/counts/policies if it fails. Diagnose the mismatch instead.

## Coordination note

Canonical `main:coordination/TEAM_STATUS.md` was read before this lane was started and no duplicate consolidation owner was found. The connector available to this ChatGPT session cannot safely patch a single row in the large shared ledger without replacing the entire file, so the branch claim was created before implementation rather than risk overwriting concurrent coordination edits. The local validation actor should refetch latest main and add/update only this lane row using normal Git tooling, preserving every concurrent row.

The concurrent `audit/pit-security-identity-stage-c-v1` lane remains authoritative for FREN/KOCI/listing-domain/universe adjudication. Stage A deliberately preserves frozen parent identities and cannot finalize the clean universe.

## Stop boundary

After one successful Stage-A runtime, record hashes/checkpoint/handoff and stop at `WAITING_FOR_IDENTITY_ADJUDICATION`. Do not fit or score V4-X, do not inspect protected outcomes, and do not execute V4-X2.

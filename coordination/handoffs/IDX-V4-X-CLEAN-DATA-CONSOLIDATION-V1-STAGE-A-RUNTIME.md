# Handoff — V4-X Clean-Data Consolidation V1 Stage-A Runtime

Branch: `data/v4-x-clean-data-consolidation-v1`
Prepared checkpoint: `docs/checkpoints/2026-08-20_V4_X_CLEAN_DATA_CONSOLIDATION_V1_PREPARED.md`
Frozen protocol: `docs/checkpoints/2026-08-20_V4_X_CLEAN_DATA_CONSOLIDATION_V1_PROTOCOL.md`

## Task

Execution-only local validation. Do not redesign methodology.

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md` and preserve all concurrent edits.
2. Confirm `PIT Security Identity / Listing-Domain V1 adversarial audit` remains separately owned; do not touch its branch/files.
3. Add/update only the V4-X clean-data consolidation row in canonical TEAM_STATUS as `ACTIVE`, owner `ChatGPT/V4-X-Clean-Data-Consolidation`, branch `data/v4-x-clean-data-consolidation-v1`, boundary: Stage-A HLC/Open/provenance only; final universe waits for identity adjudication.
4. Checkout/pull `data/v4-x-clean-data-consolidation-v1` in a separate clean worktree.
5. Read the frozen protocol and prepared checkpoint. Do not widen scope.
6. Run focused tests:
   `python -m pytest -q tests/test_v4_x_clean_data_consolidation.py`
7. If tests fail, fix only demonstrable implementation bugs while preserving the frozen contract. Commit/push the fix before runtime. Do not loosen pins/counts/policies.
8. If focused tests pass, run exactly once against the default pinned local artifacts:
   `python scripts/run_v4_x_clean_data_consolidation_v1.py`
9. On successful runtime, verify printed status is `STAGE_A_CONSOLIDATION_MATERIALIZED_WAITING_FOR_IDENTITY_ADJUDICATION`.
10. Record result checkpoint + result handoff, update only this TEAM_STATUS row to `WAITING` or `REVIEW` with manifest SHA, and stop.

## Hard prohibitions

No provider call, model fit/score/tune, target/return/rank access, protected/fresh-forward outcome access, forward-counter mutation/reset, V4-X refit, V4-X2 execution, session-window change, primary-liquidity change, FREN/KOCI/universe/listing repair, parent overwrite, or output-pin loosening.

## Required return to ChatGPT

Return only:

- final branch + HEAD;
- focused test result;
- runtime status;
- manifest path + SHA-256;
- rows/tickers;
- HLC repair rows/tickers;
- Open official/fallback/fail-closed counts;
- identity/Volume/Regular-Market-Value parity verdicts;
- TEAM_STATUS main commit;
- any implementation-only fix made.

Do not proceed to Stage B or refit.

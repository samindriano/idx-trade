# V4-X Clean-Data Consolidation V1 — Stage-B Result

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `data/v4-x-clean-data-consolidation-v1`

## Decision

`STAGE_B_SECURITY_MASTER_MATERIALIZED_REFIT_NOT_AUTHORIZED`

The independently accepted Stage-C identity result was applied exactly once
through the frozen Stage-B interface. This materializes the clean identity
bundle only. It does **not** authorize a V4-X refit, replay, forward-counter
reset, or any outcome work.

Action: `APPLY_CERTIFIED_IDENTITY_OVERLAY`  
Policy: `RESTORE_AUTHORITATIVE_HISTORICAL_MASTER_RIGHT_ONLY_IDENTITIES_V1`

## Inputs and acceptance

- Stage-C manifest SHA-256:
  `5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61`
- Stage-C status: `PIT_SECURITY_IDENTITY_STAGE_C_COMPLETE`
- Stage-C decision:
  `V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION`
- Identity acceptance SHA-256:
  `5c2a2ce214f07225c30a3f899c850117bdceb397ab3d9189443f853d4c2d5424`
- Accepted overlay SHA-256:
  `eb4050dffccfe3beb649f5f9d13eb9631be8ccfcf85751f942e936a72ce2ede8`
- Overlay rows/tickers: `2 / 2` (`FINN`, `FREN`)
- Frozen pre-reconcile security master SHA-256:
  `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240`

## Materialized bundle

External output root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_stage_b_final_20260820`

- Final security master: `979` rows / `979` tickers
- Final security master SHA-256:
  `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`
- Identity correction ledger SHA-256:
  `4d5444308534e2bfdb557292394db444fafb2d7310f9db5f45807961ba15c2ee`
- Summary SHA-256:
  `110add02978895891a96d19bb378afb01ec58e4e7f41ed6778cb2f6bf04fe6da`
- Bundle manifest SHA-256:
  `561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358`

The final manifest re-verifies all four hashes. Stage-A panel bytes remain
referenced, not rewritten:

- Stage-A manifest:
  `eaeabad3c2050142d973d3f8ec350934b995b4e890ea4a12588304d325073969`
- Stage-A clean candidate panel SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Stage-A panel rows/tickers: `981,940 / 945`
- `stage_a_panel_rewritten=false`
- `stage_a_hlc_open_changed=false`

## Guardrails

No provider calls, target numeric values, returns/ranks, protected or
fresh-forward outcomes, model fit/scoring/tuning, counter mutation, session
semantic change, liquidity-definition change, or V4-X refit occurred.

## Validation

- Focused Stage-B/consolidation tests: `15 passed`
- Explicit `py_compile`: PASS
- `git diff --check`: PASS
- Full repository pytest: `1 failed` (pre-existing/out-of-scope)
- Failure: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expected one conflict but current storage semantics correctly surfaced two
  independent conflicts (`raw_close` and `vendor_adj_close`). No source change
  was made to alter or suppress either conflict.

## Next decision boundary

Independent review must accept this frozen clean bundle before a separately
authorized deterministic V2/V4-X replay/refit. Do not refit or reset the
forward counter automatically.

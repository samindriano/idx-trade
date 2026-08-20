# V4-X Clean Consolidated Input Bundle — Final Freeze

Date: 2026-08-21 (Asia/Jakarta)
Branch: `data/v4-x-clean-data-consolidation-v1-final-input-freeze-v1`
Source head: `d134d48db635bbbae712b4d40c2b08f6f3630cee`

## Decision

`STAGE_B_SECURITY_MASTER_MATERIALIZED_REFIT_NOT_AUTHORIZED`

The accepted Stage-C PIT Security Identity correction was applied through the
frozen Stage-B interface. This is an outcome-blind input freeze only. It does
not authorize V4-X refit/scoring, forward replay, counter reset, or outcome
access.

## Fresh certified output

External root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_final_20260821_v1`

Manifest SHA-256:

`ba246efe988c9caaba1af804d1b61b316dc7ad12579959f9dd1bac37f25e4351`

| Artifact | Result / SHA-256 |
|---|---|
| final security master | 979 rows / 979 tickers; `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e` |
| identity correction ledger | 2 rows / 2 tickers (`FINN`, `FREN`); `4d5444308534e2bfdb557292394db444fafb2d7310f9db5f45807961ba15c2ee` |
| summary | `72ae7dcd24024f596ae758633f0c76abb22212240d2f0264e74ace3e71c1b1f1` |
| final manifest | `ba246efe988c9caaba1af804d1b61b316dc7ad12579959f9dd1bac37f25e4351` |

The Stage-A panel remains referenced and unchanged: `981,940` rows / `945`
tickers, panel SHA `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`.
No synthetic price rows were added; FINN/FREN are supplied through the
reconciled historical security master for downstream feature construction.

## Pinned lineage

- Stage-A manifest: `eaeabad3c2050142d973d3f8ec350934b995b4e890ea4a12588304d325073969`
- Stage-B interface helper blob: `26458824c55a2a264ed04b6bc869ef71b1ab5adb`
- Stage-B interface runner blob: `4ff0e726027eed7a3177a79841ab9cbde71964c9`
- Stage-C manifest: `5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61`
- Identity acceptance: `5c2a2ce214f07225c30a3f899c850117bdceb397ab3d9189443f853d4c2d5424`
- Accepted identity overlay: `eb4050dffccfe3beb649f5f9d13eb9631be8ccfcf85751f942e936a72ce2ede8`
- Frozen pre-reconcile security master: `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240`

Stage-C decision remains:
`V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION`.

## Validation and guardrails

- Focused Stage-B/consolidation tests: `15 passed` (`7 + 8`, cache provider disabled because the external worktree cannot write its pytest cache).
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Fresh output hashes: PASS; manifest-declared final master and ledger hashes match.
- Provider calls: `0`.
- Model fit/scoring/tuning/refit: `0`.
- Targets/labels/returns/ranks: not accessed.
- Protected/fresh-forward outcomes: not accessed.
- Forward counter: not mutated or reset.
- Stage-A panel: not rewritten.

The repository's known unrelated storage expectation failure remains outside
this input-freeze lane; no storage code was changed.

## Next boundary

Stop for independent review. A separate authorization is required for the
deterministic replay/refit. Do not reset the forward counter as part of this
bundle freeze.

# V4-X1 Clean Remediation — Final Clean Input Bundle Acceptance Pin

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x-clean-replay-refit-contract-v1`
Status: `V4_X1_FINAL_CLEAN_INPUT_BUNDLE_ACCEPTED_HASH_PINNED_EXECUTION_LOCK_NEXT`

## Decision

The V4-X clean-data consolidation bundle is accepted as the immutable clean-input dependency for the V4-X1 clean remediation contract.

This acceptance covers only the already-adjudicated clean-data scope:

- accepted H/L/C repairs;
- accepted Open repairs with fail-closed unsupported rows;
- unchanged Volume and Regular-Market Value lineage;
- reconciled historical security-master identity with the accepted generic FINN + FREN right-only restoration;
- Stage-A field-level provenance and correction lineage;
- preservation of the Stage-A clean panel bytes during Stage-B identity materialization.

This checkpoint does not authorize a model fit, historical prediction, historical performance recomputation, provider call, protected/fresh-forward outcome access, forward-counter mutation, session-semantic rewrite, V4-X2 execution, or any further data repair.

## Accepted consolidation lineage

Consolidation branch:

`data/v4-x-clean-data-consolidation-v1`

Reviewed Stage-B branch HEAD recorded in canonical coordination:

`d134d48db635bbbae712b4d40c2b08f6f3630cee`

Stage-B result checkpoint:

`docs/checkpoints/2026-08-20_V4_X_CLEAN_DATA_CONSOLIDATION_V1_STAGE_B_RESULT.md`

Stage-B result decision:

`STAGE_B_SECURITY_MASTER_MATERIALIZED_REFIT_NOT_AUTHORIZED`

## Exact accepted artifact pins

Final Stage-B bundle manifest SHA-256:

`561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358`

Stage-A manifest SHA-256:

`eaeabad3c2050142d973d3f8ec350934b995b4e890ea4a12588304d325073969`

Stage-A clean panel SHA-256:

`25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`

Stage-A field-level provenance parquet SHA-256:

`cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`

Stage-A field-level provenance CSV SHA-256:

`91cf615a9ab533a1478fbc1aecc5084341647070d091d85d5a7ee53a2ad4ccf3`

Stage-A correction ledger CSV SHA-256:

`6f883aaae54b3180bc3c38a2836b88b9cb983ed215dbb61246329a869138e125`

Final Stage-B security master SHA-256:

`51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`

Stage-B identity correction ledger SHA-256:

`4d5444308534e2bfdb557292394db444fafb2d7310f9db5f45807961ba15c2ee`

Accepted identity overlay SHA-256:

`eb4050dffccfe3beb649f5f9d13eb9631be8ccfcf85751f942e936a72ce2ede8`

Stage-C PIT Security Identity manifest SHA-256:

`5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61`

## Population / identity invariants

- Stage-A clean panel: `981,940` rows / `945` panel tickers.
- Final security master: `979` rows / `979` tickers.
- Accepted identity overlay: `2 / 2` (`FINN`, `FREN`).
- Stage-B did not rewrite the Stage-A panel.
- Stage-B did not alter the accepted H/L/C or Open corrections.
- Volume parity: PASS.
- Regular-Market Value parity: PASS.

The difference between panel ticker count and security-master ticker count is not interpreted here as a new universe repair request. Clean Phase A must apply the frozen parent V4-X1/V4-3R decision-universe and PIT listing-domain semantics deterministically and report the resulting support identities.

## Corporate Action dependency

The separate clean-remediation Corporate Action disposition is already accepted:

`V4_X1_CLEAN_CA_DISPOSITION_ACCEPTED_REUSE_PARENT_CA80_RECOMPUTE_ON_CLEAN_INPUT`

Clean Phase A must therefore reuse the frozen V4-3R CA80 semantics/evidence and recompute state/support on this accepted clean input. If the clean support no longer satisfies the frozen CA80 contract, execution must stop fail-closed before any model fit.

## Next authorized step

Create one hash-only Phase-A execution lock that may pin:

- this acceptance checkpoint;
- the exact final clean bundle hashes above;
- the already-accepted CA disposition;
- the exact runtime environment and frozen scientific code blobs.

The execution lock may not change features, targets, folds, universe rule, CA semantics, observed-row window semantics, model family, preprocessing, learner parameters, or historical training boundary.

After that separate lock is independently reviewed, Phase A may perform the previously frozen outcome-blind structural clean replay only.

## Explicitly still prohibited

- model fitting;
- historical prediction generation;
- historical performance recomputation;
- target numeric value inspection during Phase A;
- provider/network calls;
- protected/fresh-forward outcome access;
- current forward-counter reset/mutation;
- V4-X2/session-aligned implementation;
- post-result tuning or rescue;
- further data corrections inside the clean replay lane.

Final decision:

`ACCEPT_FINAL_CLEAN_INPUT_BUNDLE_FOR_V4_X1_CLEAN_REMEDIATION`

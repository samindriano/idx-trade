# Ranking V4 target-support census — independent acceptance

Date: 2026-08-17 (Asia/Jakarta)
Reviewed branch: `research/idx-v4-target-support-census-remediation-v1`
Reviewed HEAD: `a2a3c30cd85d02de3e340536c376752cdf4456b0`
Status: `V4_TARGET_SUPPORT_CENSUS_REMEDIATION_ACCEPTED_6X100_FEASIBLE`

## Independent review verdict

**ACCEPTED.** The remediated census is decision-valid for the narrow question of whether the locked V4 H5/H10/consensus support rules can technically supply six 100-session validation blocks before any V4 outcome/performance run.

The prior result at `research/idx-v4-target-support-census-v1@5f3c2d7b66cf66b2676ba0a409cdc2f4c9ca8f5d` is superseded for decision use because it omitted the already accepted Yahoo+TradingView Open derivative and therefore materially understated `Open_(t+1)` support.

## Findings accepted

- exact decision population: 981,940 rows / 945 tickers / 1,260 official sessions;
- accepted Yahoo+TradingView derivative Open support: 938,139 rows;
- independently verified CA-scale overlay: 2,184 rows;
- derivative/overlay overlap: 0 rows;
- final Open support: 940,323 / 981,940 = 95.7618%;
- H5 target support: 913,621 rows;
- H10 target support: 906,377 rows;
- both-target support: 899,739 rows;
- both-horizon CA continuity: 938,553 rows;
- eligible sessions under the locked >=90% date gate: H5 910, H10 891, consensus 815;
- each relevant sequence therefore exceeds the frozen 600-session technical requirement.

Pinned eligible-list SHA-256 values accepted:

- H5: `a58b0ef0f6562ad417d0f8c2dce24b811eee865bc82706499cceb7d51cea6d1d`
- H10: `37b44ffbec99c7fd1e3024c8447ab0128177ce73a0149f85af7cd85db1baf634`
- consensus: `7336454fed8aaefffbc92cfae5860a1486c11a9235820894eb896bf4f82312ee`
- full 1,260-session identities: `c5a0d03b17234cc657bd472f23c3fbaf66698883768493641ee30021f97f2ae0`

## Review of the remediation

The code now requires the hash-pinned Yahoo+TradingView derivative and exact one-to-one ticker/date identity before support accounting. The CA-scale overlay is applied only to still-missing derivative keys, and the accepted run reports zero overlap. Parent tradability semantics are preserved: conflicting anchors remain `AMBIGUOUS`. No model, return/label, IC/performance, provider, or new corporate-action acquisition path is introduced by the remediation.

The interpretation of `100 consecutive eligible signal sessions` as consecutive observations in the ordered eligible-session sequence is consistent with the locked V4-2 wording. Dates below the >=90% gate remain visible in the full census but do not enter the corresponding eligible sequence.

## Provenance warning

`docs/SIGNAL_RESEARCH_HLCV_CONTRACT.md` is not present at the parent-pinned local path and no alternate bytes were substituted. A repository path-history query also found no tracked commit for that exact path. This is a reproducibility/provenance warning, **not a reason to reverse the technical support-feasibility verdict**, because all data artifacts actually consumed by the census are independently SHA-pinned.

However, downstream V4 execution must not claim fully self-contained reproducibility until the missing contract's exact bytes/identity are recovered or the controlling semantics are re-pinned through an explicit provenance-remediation checkpoint without changing scientific rules.

## Scientific boundary after acceptance

This acceptance does **not** authorize opportunistic target inspection, model fitting, or performance-driven design changes.

Before V4 historical targets are materialized/inspected, the remaining pre-outcome design must be frozen, including:

1. exact H5/H10/consensus fold identities and purge boundaries derived only from the accepted eligible sequences;
2. the V4 experimental control and any initial challenger information block;
3. learner/model family and training configuration;
4. paired common-support comparison rules and numerical promotion thresholds;
5. handling of H5/H10/consensus shared-vs-separate fold identity.

Those items belong to V4-3 preregistration. Historical target values remain unseen until that contract is locked.

Verdict:

`V4_TARGET_SUPPORT_CENSUS_REMEDIATION_ACCEPTED_6X100_FEASIBLE`

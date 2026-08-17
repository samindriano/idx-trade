# Ranking V4-3 primary-liquid support census — independent acceptance

Date: 2026-08-17 (Asia/Jakarta)
Reviewed branch: `research/idx-ranking-v4-3-preregistration-v1`
Reviewed HEAD: `55440cac2b605c687963ce858ccd3610659ddba0`
Scientific preregistration base: `8dbde070b18edf432348062e5a9218f6ef2665f9`
Status: `V4_3_PRIMARY_LIQUID_SUPPORT_ACCEPTED_6X100_IDENTITIES_FROZEN`

## Independent review verdict

**ACCEPTED.** The V4-3 primary-liquid support census is decision-valid for the narrow pre-outcome question it was authorized to answer: whether the frozen `V4_PRIMARY_LIQUID_CAUSAL_V1` universe can supply the preregistered shared last-600 consensus validation calendar and six 100-session folds without changing the V4-3 scientific configuration.

No V4 return, target rank, fitted model, prediction, IC, Top-30 result, raw-return performance diagnostic, provider call, or protected/fresh-forward outcome was required or inspected for this acceptance.

## Configuration immutability review

`8dbde070... -> 55440cac...` is exactly one commit ahead. The diff adds only:

- support/eligible/fold artifacts;
- the support result checkpoint;
- the support-result handoff.

`config/ranking_v4_3_preregistration.json`, V4-0/V4-1/V4-2 contracts, feature/model source, and scientific thresholds are unchanged.

The runtime support manifest independently pins the preregistration bytes as:

`835da85549b1d6874cb2ab49a029b9f4358fdf28cb8379b3f9df105835b05849`.

## Accepted support result

Frozen primary-liquid decision universe:

- 740 tickers;
- 348,765 decision rows;
- 1,241 sessions with at least one scored row;
- causal 60-official-session liquidity window;
- minimum 20 finite Regular-Market value observations;
- median Regular-Market value threshold IDR 1,000,000,000;
- no Top-N liquidity rank filter.

Outcome-blind eligible-session census:

- H5: 1,108;
- H10: 1,102;
- consensus: 1,100.

All materially exceed the frozen 600-session minimum.

## Exact validation identity review

The consensus eligible list is hash-pinned:

`06f7af7d0bc34c1714ed3c19684177cd27dd911c11fd509c231b9bdfb90f970b`.

The last 600 rule is internally consistent:

- zero-based consensus eligible position 500 is official session index 650 / 2023-12-28;
- the final eligible position 1099 is official session index 1249 / 2026-07-17;
- therefore exactly 600 selected validation sessions are produced;
- the selected tail happens to be contiguous in official-session index space from 650 through 1249, so there are no hidden eligible-calendar gaps inside the frozen validation period.

Validation-fold artifact SHA-256:

`91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915`.

Fold boundaries are:

| Fold | Official indices | Dates | Max training signal index |
|---:|---|---|---:|
| 1 | 650–749 | 2023-12-28 → 2024-06-10 | 639 |
| 2 | 750–849 | 2024-06-11 → 2024-10-31 | 739 |
| 3 | 850–949 | 2024-11-01 → 2025-04-10 | 839 |
| 4 | 950–1049 | 2025-04-11 → 2025-09-12 | 939 |
| 5 | 1050–1149 | 2025-09-15 → 2026-02-06 | 1039 |
| 6 | 1150–1249 | 2026-02-09 → 2026-07-17 | 1139 |

The purge implementation is correct for the frozen H10 horizon: if validation starts at official session `s`, training signals `s-10 ... s-1` are excluded and the latest training signal is `s-11`.

The final validation signal date is 2026-07-17, which leaves the frozen H10 target mature by the historical-development cutoff 2026-07-31. No post-cutoff future price is needed for historical-development labels.

## Support-run implementation audit

The support runner:

- hash-verifies the official calendar, immutable panel, tradability evidence, accepted Yahoo+TradingView Open derivative, verified CA Open overlay, signal contract, and preregistration;
- rejects duplicate panel/Open identities;
- rejects known label/outcome-like columns in the input panel;
- computes the primary-liquid state only from EOD/current-and-prior official-session information;
- keeps explicit ACTIVE / NO_TRADE / SUSPENDED / UNKNOWN / AMBIGUOUS / NO_FUTURE_SESSION states;
- applies the frozen 90% date-level target-support and CA-integrity gates;
- refuses to materialize folds when consensus support is below 600;
- writes the immutable small artifacts and their SHA-256 identities without fitting a model.

No decision-changing implementation defect was found in the bounded support/fold materialization path.

## Accepted provenance

Support manifest SHA-256:

`6cb8df059d310bb337ffe7f5026d416f0e15252c79ecc04e6c597925a0d243a4`.

The manifest records:

- `outcome_blind = true`;
- `returns_or_target_ranks_loaded = false`;
- `model_fit = false`;
- `provider_calls = false`.

The previously recovered signal-research contract remains pinned at SHA-256:

`ffff2d21b275744a3a2b74c2f7d32be7b589f3c46cf9950c5ff45c48e5bffd73`.

## Scientific boundary after acceptance

This acceptance freezes the support/fold identities. It does **not** yet authorize first model fit.

Before any V4 historical target or prediction is produced, the remaining pre-fit engineering gates are:

1. implement and freeze the exact target/feature/train/evaluate code path against synthetic/non-outcome fixtures;
2. hash-pin that execution code plus the accepted support/fold artifacts;
3. capture and hash-pin the exact local Python/numpy/pandas/scipy/scikit-learn/pyarrow/joblib/threadpoolctl runtime used for first fit;
4. verify effective `HistGradientBoostingRegressor` and `SimpleImputer` parameters exactly match the preregistration;
5. verify the worktree/code identity is clean and immutable for the one-shot historical-development run.

Package/runtime choice may not change after V4 target/performance access to rescue a result.

Verdict:

`V4_3_PRIMARY_LIQUID_SUPPORT_ACCEPTED_6X100_IDENTITIES_FROZEN`

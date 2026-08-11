# OHLCV O2 Minimality — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-minimality-v1`
Reviewed runtime HEAD: `94ed3ae3272256231259fd03146f2e4662cb410a`
Decision: `O2_FULL_3_SELECTED_FOR_FINAL_FREEZE`

## Review

The frozen eight-model minimality ablation is accepted as valid historical-development evidence.

Exact population and model contract were preserved: 278,168 rows / 729 tickers, common-support key SHA-256 `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`, canonical V3-B 33-feature baseline, exact six folds, H10 labels, HGB parameters/evaluator/seed, and accepted O2 geometry values. Parent O2 baseline/full metrics reproduced to numerical precision and no fresh-forward outcomes, provider calls, tuning, or final refit occurred.

## Representation decision

Advance the accepted full three-feature representation:

- `open_position`
- `open_to_high`
- `open_to_low`

with feature-order SHA-256 `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`.

Rationale:

1. `O2_FULL_3` retains the strongest frozen survivor evidence: median paired PR-AUC delta vs baseline `+0.007276`, lower quartile `+0.004710`, positive folds `6/6`.
2. Every reduced representation is weaker than full O2 in five of six folds. The strongest reduced pair by median uplift, `O2_PAIR_POSITION_LOW`, has median baseline uplift `+0.005940` and median paired delta versus full O2 `-0.001513`; `O2_PAIR_HIGH_LOW` retains 6/6 positive folds but has median paired delta versus full O2 `-0.001663`.
3. The frozen protocol intentionally did not define a post-hoc non-inferiority margin. Therefore it would be methodologically unsound to declare a reduced representation equivalent after seeing the results.
4. Algebraic redundancy is acknowledged. For this fixed HGB architecture, the ablation shows that exposing the same underlying geometry through all three coordinates improves the learned partitioning enough to produce more robust historical-development evidence. This adds only three deterministic causal columns and does not add provider or target information.

This does not establish independent forward validity and does not replace canonical V3-B yet.

## Authorization

Authorized next step: separately frozen final-candidate freeze and one final historical refit of `O2_FULL_3` on the exact accepted 278,168-row common-support population, with the existing HGB parameters and no tuning. Persist model/feature/data hashes and a forward-scoring contract. Do not access post-2026-07-31 outcomes.

Not authorized: O3/new Open features, tuning, regime/interaction search, canonical V3-B overwrite, execution/PnL, paper/live, or any forward-outcome evaluation before a separate forward-validation specification is frozen.

# Ranking V2 Forensic Audit — Stage 3: Adversarial / Red-Team Review

Date: 2026-08-16 (Asia/Jakarta)
Status: `FORENSIC_STAGE3_RECORDED_NO_EXPERIMENT`
Branch: `research/idx-ranking-v1-forensic-audit-v1`

## Scope

Documentation-only adversarial review of Ranking V2. No model fit, outcome rerun, provider call, protected/fresh-forward outcome access, feature-importance mining, rescue, threshold search, or canonical model mutation was performed.

The purpose is to attack the strongest interpretation of V2 before a later stage ranks criticality and defines remediation.

## 1. The current trusted V2 evidence is the corrected PIT-safe replay, not the original champion metrics

The later PIT-safe replay explicitly classifies the old V2/V3-B/O2 fitted models and metrics as `LEGACY_CONTAMINATED_REFERENCE`. On the corrected PIT-safe reconstruction, the exact frozen V2 candidate set was replayed and `HGB_XS_MARKET` was selected again, so V2 survives as the clean historical-development V2 candidate.

However, the corrected metrics materially weaken the old claim that V2 clearly improved lower-tail robustness versus V1.

Original historical review:

| model | median PR delta | q25 PR delta | median ROC |
|---|---:|---:|---:|
| V1 HGB control | 0.02234800 | 0.01684875 | 0.51901000 |
| HGB_XS_MARKET | 0.02387950 | 0.01940150 | 0.52441000 |
| V2 minus V1 | +0.00153150 | +0.00255275 | +0.00540000 |

Corrected PIT-safe replay:

| model | median PR delta | q25 PR delta | median ROC | median Q5-Q1 |
|---|---:|---:|---:|---:|
| V1 HGB control | 0.02310942 | 0.01766978 | 0.51829043 | 0.03002639 |
| HGB_XS_MARKET | 0.02419450 | 0.01265903 | 0.52517063 | 0.05308354 |
| V2 minus V1 | +0.00108508 | **-0.00501075** | +0.00688020 | +0.02305715 |

Thus the clean replay still shows a small median PR improvement, stronger median ROC and stronger Q5-Q1, but **the q25 PR comparison reverses against V2**. The earlier narrative that V2's main gain was lower-tail PR robustness over V1 is therefore not stable under the corrected lineage.

This does not reverse the official replay verdict because the V1 control was intentionally not champion-eligible under the frozen V2 contract.

### Counterfactual governance observation

If the frozen V2 champion-selection rule were applied counterfactually with `V1_HGB_CONTROL` allowed to compete, the clean median PR gap between V2 and V1 is only `0.00108508`, inside the frozen `0.002` practical-tie band. The next tie-break is q25 PR delta; V1's clean q25 exceeds V2's by `0.00501075`, well outside that tie band. Under that counterfactual, V1 would win the q25 stage.

This is **not** an official model verdict and must not be used to rewrite the frozen experiment. It is an adversarial observation showing that clean V2 has not established robust incremental superiority over its V1 control under the same selection priorities.

## 2. The late-period robustness claim is especially vulnerable

The original V2 champion review reported V2F6 PR delta about `+0.018643` and ROC about `0.493102`.

The later accepted Clean V2 base used by exact-common-support Foreign Flow experiments reports V2F6 PR delta `+0.003791` and ROC `0.487025`, while Q5-Q1 remains positive around `0.045169`.

So the broad PR discrimination in the difficult late fold is much weaker under clean lineage even though top-vs-bottom bucket ordering remains positive. V2 is therefore not a demonstrated cure for the V1 late-regime failure; at best, it is a partially more resilient representation whose late-fold evidence remains mixed.

## 3. V2 can robustly learn the wrong estimand

V2 inherits without modification:

- H10 first-touch target;
- `TP_FIRST`/`SL_FIRST` resolved-only model population;
- ATR14 barrier geometry;
- `Close_t` label reference;
- after-close signal timing.

Therefore all V1 P0 questions remain open. Better discrimination of `TP_FIRST` vs `SL_FIRST | future barrier resolved` does not establish better stock selection over the full decision universe, and it does not establish executable edge from a price obtainable after the close-t signal.

A statistically cleaner V2 can therefore be a better model of an economically incomplete target.

## 4. Row-pooled metrics do not equal the product's daily decision objective

The evaluator computes PR-AUC and ROC-AUC on all validation rows pooled together. Within-date buckets are created, but `bucket_summary()` then pools all rows in each bucket when computing TP rates.

Consequences:

- dates with more resolved eligible rows receive more weight;
- a 100-session validation fold is not an equal-weight average of 100 daily ranking decisions;
- dates/regimes with more future barrier resolution contribute more observations to both the primary PR metric and the bucket metrics.

Because the product makes one cross-sectional decision per session, the evaluation unit is not perfectly aligned with the operational decision unit.

## 5. Resolved-only conditioning and pooled weighting interact

Future barrier resolution is itself related to volatility, liquidity, momentum and regime. V2 market context is correctly computed from the full causal primary-liquid universe before labels, but model fitting/evaluation use only future-resolved rows.

Therefore a high-volatility date can both change V2's market-state inputs and alter how many rows from that date enter the target/evaluation population. This is not conventional feature leakage; it is an estimand/weighting problem that can make apparent regime robustness partly reflect changing future-resolution composition.

## 6. The removal of explicit time proxies does not prove V2 is free of era fingerprints

V2 removes `observed_session_count` and `security_age_sessions_exact`, which is a sound control. But it adds `market_primary_liquid_count` directly, and several market medians/breadth variables can strongly identify historical environments.

The primary universe itself uses a nominal IDR 1 billion 60-session median-value threshold. As listings, liquidity and nominal market values evolve, universe size/composition can drift with calendar time. Thus `market_primary_liquid_count` is both legitimate market state and a plausible implicit era proxy.

No claim is made here that the model actually exploits it as a calendar identifier; that mechanism has not been independently proven.

## 7. Cross-sectional ranks are conditional on a changing peer set

A ticker's percentile rank can move while the ticker's own raw state is unchanged if:

- IPOs enter;
- suspensions/no-trade states change;
- securities cross the liquidity threshold;
- market breadth/composition changes.

That is partly the intended meaning of a relative signal, but it also means rank stability depends on universe construction quality. The PIT repair showed that even a one-row listing-domain correction propagated into hundreds of market-context rows, demonstrating that cross-sectional context can amplify small upstream identity changes across same-date peers.

## 8. The 25-feature representation is not a clean test of normalization

For six dimensions the model receives market median plus stock-minus-market value, which reconstructs the raw stock value, together with the cross-sectional rank. Structure features also contain algebraic redundancy.

Therefore the success of `HGB_XS_MARKET` cannot be causally attributed to normalization alone. The architecture gives HGB several threshold-friendly parameterizations of overlapping information and explicit time-varying context.

This is useful engineering, but a weaker scientific statement than `cross-sectional normalization solved regime transportability`.

## 9. Six folds are not six independent replications

The V2 folds are contiguous chronological validation windows with expanding, nested training prefixes. They are much better than a random split, but `6/6 positive folds` should not be read like six independent experiments:

- training samples overlap heavily;
- adjacent market regimes are serially dependent;
- all candidate design choices were informed by the already-consumed V1 history;
- all rows through 2026-07-31 are explicitly development knowledge.

The historical folds establish development consistency, not independent confirmation.

## 10. The candidate-selection process cannot establish incremental superiority over V1

`V1_HGB_CONTROL` was deliberately declared non-champion-eligible before outcome execution. This was legitimate governance for a new V2 architecture, but scientifically it means the official verdict answers:

> Which eligible V2 candidate is best?

not:

> Is V2 robustly superior to V1?

The corrected replay makes this distinction material because V2's median PR advantage over V1 is small while its q25 PR is worse.

## 11. The ranking-native question remains open

The pairwise challenger used only ten XS features, a linear logistic utility and a bounded pair sample. It did not test a nonlinear ranking objective conditioned on the market context that appears important to V2.

Its failure therefore does not establish that pointwise HGB is the correct objective for a daily stock-ranking product.

## 12. Market-relative signal may still contain sector exposure

V2 compares each stock mainly with the entire broad-liquid market. A stock can look strong versus market because its sector is temporarily strong, without possessing stock-specific alpha.

Sector-relative features were correctly blocked because a PIT-safe historical sector map was unavailable. Therefore V2 cannot distinguish stock-specific relative strength from sector-rotation exposure as cleanly as a mature model might.

## 13. Nominal liquidity threshold may distort temporal comparability and economic relevance

The primary broad-liquid universe requires a 60-session median regular-market value of at least IDR 1 billion. A fixed nominal threshold across years is not inflation/market-scale neutral and may admit materially different execution-quality stocks across periods.

At the same time, IDR 1 billion can be too permissive for a portfolio that eventually trades meaningful size. Thus V2's research universe and eventual executable universe are not proven equivalent.

## 14. PR/ROC/Q5-Q1 are signal diagnostics, not portfolio utility

Even positive cross-sectional ordering does not establish:

- realistic next-session entry;
- turnover and rank stability;
- slippage/market impact;
- capacity;
- portfolio concentration;
- opportunity cost across simultaneous names;
- realized risk-adjusted PnL.

The original V2 contract correctly avoided execution-PnL claims. The red-team conclusion is that these omissions are still central before interpreting a small statistical edge as economic alpha.

## 15. No uncertainty statement surrounds the small V2-vs-V1 incremental PR effect

The clean median PR improvement over the V1 control is only about `+0.001085`. Because folds are serially dependent and nested, a naive IID standard error would be inappropriate. V2 therefore does not currently quantify how stable that incremental effect is under block/time uncertainty.

Any future uncertainty analysis should be preregistered around the decision-date/time structure and must not be used to retroactively rescue the consumed historical experiment.

## Red-team severity shortlist

### Foundation-threatening

1. inherited resolved-only target/estimand;
2. inherited `Close_t` versus executable `t+1` entry mismatch;
3. clean replay no longer supports the old lower-tail robustness story versus V1;
4. official V2 selection never allowed V1 to win, so `V2 selected` is not `V2 proved superior to V1`.

### Architecture-threatening

5. row-pooled metrics versus date-level decision unit;
6. future-resolution composition interacting with regime and weighting;
7. market/universe context acting as possible era fingerprint;
8. ranking-native objective not actually tested on the successful contextual representation;
9. sector exposure unresolved inside market-relative strength.

### Important but secondary

10. redundancy / raw-value reconstruction inside 25 features;
11. changing-peer-set sensitivity of percentile ranks;
12. nominal liquidity threshold comparability/executability;
13. correlated six-fold evidence being weaker than six independent replications;
14. absence of turnover/capacity/economic-utility validation;
15. no time-aware uncertainty estimate for the small incremental V2-vs-V1 edge.

## Stage-3 verdict

`V2_SURVIVES_AS_CLEAN_CONTEXTUAL_BENCHMARK_NOT_AS_PROVEN_INCREMENTAL_SUCCESSOR`

The corrected PIT-safe replay is important positive evidence: V2's `HGB_XS_MARKET` remains the selected **V2 candidate** after lineage repair. But the stronger historical story — that V2 clearly and robustly dominates V1 by fixing its regime failure — does not survive adversarial review. The clean evidence is mixed: median discrimination and Q5-Q1 improve, q25 PR worsens, the hard late fold remains weak, and all V1 target/execution P0 issues remain inherited.

Next stage should answer these attacks, rank criticality, specify what is already falsified versus still unknown, and define bounded remediation principles for a future clean-generation ranker. No V2 rescue experiment is authorized by this checkpoint.
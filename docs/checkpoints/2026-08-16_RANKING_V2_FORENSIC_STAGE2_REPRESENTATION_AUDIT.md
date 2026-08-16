# Ranking V2 Forensic Audit — Stage 2: Representation and Current-Data Lessons

Date: 2026-08-16 (Asia/Jakarta)
Status: `FORENSIC_STAGE2_RECORDED_NO_EXPERIMENT`
Branch: `research/idx-ranking-v1-forensic-audit-v1`

## Scope

Read-only forensic interpretation of accepted Ranking V2. No model fit, outcome rerun, provider call, protected/fresh-forward outcome access, threshold search, candidate rescue, or canonical model mutation was performed.

This checkpoint follows the Ranking V1 forensic audit and records what V2 actually learned before a separate adversarial/red-team stage.

## 1. V2 is representation engineering, not a new information set

The V2 champion `HGB_XS_MARKET` keeps the V1 target/universe/timing semantics and the same HGB hyperparameters. The information source remains daily HLCV-derived state; Open is explicitly prohibited. The material change is representation:

- 10 same-date cross-sectional percentile ranks;
- 9 continuous market-state variables;
- 6 stock-minus-market features;
- removal of `observed_session_count` and `security_age_sessions_exact` from the V2 core.

Thus V2 does not answer the V1 P0 questions around resolved-only H10 barrier target, Close_t execution reference, or executable t+1 entry.

## 2. The 25 V2 features do not represent 25 independent information dimensions

For six source dimensions, V2 includes three views of essentially the same contemporaneous state:

- stock percentile rank;
- market median;
- stock minus market median.

For each of these six dimensions, raw stock value is exactly reconstructible as:

`raw_stock_value = market_median + market_relative_value`

Affected dimensions:

- `close_return_5`;
- `close_return_20`;
- `atr14_over_close`;
- `close_position_20`;
- `relative_volume_20`;
- `log_regular_value_relative_20`.

Therefore `HGB_XS_MARKET` is not a purely normalized model. It is a hybrid absolute + relative + market-context representation.

The structure family is also internally redundant by construction. For the 20-bar geometry, when finite:

`close_position_20 = distance_low_20_atr / (distance_low_20_atr + distance_high_20_atr)`

because the ATR denominator cancels. Multiple parameterizations can still help a tree model form useful thresholds, but they should not be mistaken for independent sources of alpha.

## 3. Pure cross-sectional normalization did not beat the V1 control

Historical-development aggregate:

- `V1_HGB_CONTROL` median PR delta: `0.0223480`;
- `HGB_XS` median PR delta: `0.0184815`;
- `HGB_XS_MARKET` median PR delta: `0.0238795`.

Replacing the raw V1 representation with only cross-sectional ranks reduced median PR delta by about `-0.0038665` versus the V1 control. Adding market state plus stock-minus-market context then raised `HGB_XS_MARKET` by `+0.0053980` over `HGB_XS` and by only about `+0.0015315` over the V1 control.

The defensible lesson is therefore not `ranks > raw features`. It is closer to:

> Preserve stock state, but express it jointly with contemporaneous market-relative position and market state.

## 4. The main V2 benefit looks more like robustness stabilization than a large average-alpha increase

Versus the same-fold V1 control, the champion improved median PR delta only about `+0.0015315`, while the robustness diagnostics moved more materially:

- q25 PR delta improvement about `+0.0025528`;
- median ROC improvement `+0.005400`;
- median Q5-Q1 improvement about `+0.0201875`;
- worst-fold PR delta `0.008789` versus V1 control `0.000785`.

This suggests market context may be more valuable as a stabilizer/conditioner across environments than as a large standalone source of incremental alpha. This is an interpretation, not a causal proof.

## 5. The V2 pairwise test does not close the objective-mismatch question

`PAIRWISE_LOGISTIC_XS` was a legitimate bounded challenger, but it tested only:

- 10 XS-rank features;
- linear logistic utility;
- deterministic within-date positive/negative pairs;
- maximum 256 unique pairs per date.

It did not test nonlinear ranking with the successful V2 market-context representation. Same-date market constants would also cancel in simple pair differences unless the architecture explicitly models market-state-conditioned ranking interactions.

Therefore its weak result does not establish that ranking-native objectives are inferior for this problem. It establishes only that the exact frozen linear pairwise-XS construction did not match HGB_XS_MARKET.

## 6. Current Open data changes what can be tested, but not in the simplistic way

The later clean V2 Open experiment had 277,244 common-support rows versus 292,631 clean-V2 rows, approximately 94.74% support. This is materially better historical Open availability than when V1/V2 were designed.

However two compact additive Open families failed the preregistered paired gate:

- V2.1 same-day Open geometry: median paired PR delta `+0.00007359`, q25 `-0.00250461`, 3/6 positive folds;
- V2.2 previous-active-range opening displacement: median `+0.00029955`, q25 `-0.00240718`, 3/6 positive folds.

Verdict remained `RETAIN_CLEAN_V2`.

This does not make Open unimportant. The more important new capability is that historical Open can now support a direct audit of the old execution/reference mismatch: information fixed after close t, realistic executable entry at Open_(t+1), then future outcome. That P0 question was never repaired by Ranking V2 and is distinct from appending Open_t as another predictor.

## 7. Foreign Flow results reinforce the V2 representation lesson rather than invalidate it

Two direct additive Foreign Flow experiments against Clean V2 failed:

- Foreign Flow V1 median paired PR-AUC delta `-0.002658935`, q25 `-0.003018476`, positive folds 2/6;
- Foreign Flow V2 Core median paired PR-AUC delta `-0.004293753`, q25 `-0.004526346`, positive folds 1/6.

The evidence does not support `more causal data columns -> stronger universal H10 ranker`.

A more coherent interpretation is that participant flow may be conditional/setup context whose meaning depends on price state, participation, liquidity and supply rather than a universal additive block. This interpretation is consistent with the post-V2 Foreign Flow architecture direction but is not a new historical-alpha claim.

## 8. Volume remains semantically under-specified without supply

V2 still represents volume primarily through own-history ratios and same-date market-relative versions. The same number of shares/value traded can have very different economic meaning under different tradable supply.

The current statutory free-float work materially improves source availability but is not a simple clean full-history denominator yet. The generalized official LBRE monthly history currently covers position months 2024-04 through 2026-06 with substantial issuer coverage, explicit unresolved lineage, and fail-closed gaps. At the 2025-12 cross-source reconciliation it records 260 AGREE, 625 CONFLICT and 38 SINGLE_SOURCE states. The source contract therefore must preserve source identity/conflict semantics rather than silently collapsing to one canonical percentage.

Because the free-float history begins much later than the V2 development history, any future supply-adjusted historical experiment would also have materially narrower temporal support and must not be presented as a direct full-six-fold replacement without a new support contract.

## 9. Intraday and corporate-action data should not be forced into a V2 retrofit yet

Historical intraday admission is still not complete for a full-universe apples-to-apples V2 experiment, and corporate-action publication linkage is still a bounded provenance/event-ledger problem. These sources can later become price-path/confirmation or event-state layers, but they are not justification to reopen the closed V2 candidate set.

## 10. What should survive from V2 into a future clean-generation ranker

Retain as design principles, not immutable features:

1. same-date cross-sectional framing;
2. explicit continuous market context;
3. stock-relative-to-market representation;
4. chronological expanding validation with purge/maturity gaps;
5. exact common-support comparisons;
6. robustness/worst-fold and top-tail diagnostics in addition to average discrimination;
7. frozen pre-outcome candidate families and no-rescue discipline.

Do not automatically retain:

- the resolved-only H10 first-touch estimand;
- `Close_t` execution reference;
- all 25 exact feature columns;
- HGB as mandatory learner;
- the exact 20/60 lookbacks;
- raw additive Open/Foreign/Financial-style feature-block expansion.

## Stage-2 verdict

`V2_REPRESENTATION_LESSON_RETAIN_CONTEXTUALIZATION_NOT_EXACT_ARCHITECTURE`

The strongest V2 lesson is that **contextualization reduces transport failure**. The evidence does not justify treating the 25-feature champion as a fundamentally new information-rich alpha engine. V2 is best viewed as a stronger, more context-aware benchmark whose average incremental edge over the V1 control remains small.

Next forensic stage: adversarially test whether the apparent robustness itself could be partly explained by redundancy, market/time proxies, metric/selection effects, target geometry, universe mechanics, or development-period reuse. No V2 rescue or new outcome experiment is authorized by this checkpoint.

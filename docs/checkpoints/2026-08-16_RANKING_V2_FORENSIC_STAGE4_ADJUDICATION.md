# Ranking V2 Forensic Audit — Stage 4: Adjudication and Inheritance Rules

Date: 2026-08-16 (Asia/Jakarta)
Status: `FORENSIC_STAGE4_RECORDED_NO_EXPERIMENT`
Branch: `research/idx-ranking-v1-forensic-audit-v1`

## Scope

Documentation-only adjudication of the Stage-3 adversarial findings. No model fitting, outcome rerun, provider call, feature-importance mining, protected/fresh-forward outcome access, metric rescue, threshold search, candidate rescue, or canonical model mutation was performed.

The goal is to decide which attacks are fatal to interpretation, which are design/evaluation limitations that a future clean-generation model must repair, which are open hypotheses rather than demonstrated defects, and which original V2 principles should remain as benchmark discipline.

## Executive adjudication

Ranking V2 survives as the strongest clean historical contextual benchmark currently available, but it should not be treated as a proven incremental successor to Ranking V1 and should not define the next model's target or execution semantics.

The Stage-3 findings separate into four classes:

1. **Research-definition blockers**: resolved-only target and Close_t execution/reference mismatch. These are fatal to any claim that V2 directly estimates the final executable stock-selection problem. A future generation must reopen target and entry semantics from scratch; feature/model tuning cannot repair them.
2. **Comparative-claim blockers**: clean q25 reversal against V1 and V1's non-eligibility in champion selection. These do not invalidate the frozen V2 experiment, but they invalidate the stronger narrative that V2 robustly proved superiority over V1.
3. **Evaluation/architecture requirements**: row-pooled weighting, future-resolution composition, ranking-objective uncertainty, possible era fingerprints, sector exposure and changing-peer dependence. These are repairable only prospectively under a new preregistered contract, not by retroactive V2 rescue.
4. **Secondary hardening / scope boundaries**: representation redundancy, nominal liquidity threshold, correlated-fold interpretation, portfolio utility and uncertainty estimation. Important, but not reasons to discard V2 as a benchmark.

## 1. Resolved-only H10 target — `MUST_CHANGE_RESEARCH_DEFINITION`

### Attack

V2 models `TP_FIRST` versus `SL_FIRST` only after the future path resolves into one of those two states. `NO_BARRIER_HIT`, ambiguous and other unresolved states do not enter the binary model population.

### Adjudication

**Foundation-level issue for the final product, but not a methodological invalidation of the frozen experiment.** V2 can be perfectly causal and statistically valid for the conditional estimand it chose while still answering the wrong economic question for daily stock selection.

The problem cannot be repaired by:

- adding more features;
- changing HGB parameters;
- reweighting existing resolved rows;
- ranking the same scores differently.

Future design must define the decision population before outcomes exist and preserve economically relevant non-hit/abstention states rather than conditioning the entire training/evaluation population on future barrier resolution.

No exact replacement target is selected by this forensic audit; target design remains intentionally open.

## 2. Close_t reference versus executable next-session entry — `MUST_CHANGE_RESEARCH_DEFINITION`

### Attack

The signal is known only after the close of session t, while label barriers are referenced to `Close_t`. A tradable implementation would generally enter no earlier than a next-session mechanism such as Open_(t+1) or another explicitly observable execution rule.

### Adjudication

**Foundation-level execution-semantics issue.** V2's signal research remains internally valid, but it cannot by itself support an executable edge claim.

The now much better historical Open availability is useful primarily because it makes a future execution/reference audit possible. The already-failed compact additive Open feature experiments do not answer this question; adding Open_t predictors and moving the economic entry reference to t+1 are different experiments.

A future clean-generation specification must freeze decision timestamp, earliest executable entry reference, and outcome clock before predictors are chosen.

## 3. Clean q25 reversal versus V1 — `INVALIDATES_STRONG_ROBUSTNESS_NARRATIVE_NOT_V2`

### Attack

On corrected PIT-safe replay, HGB_XS_MARKET retains a small median PR advantage and stronger ROC/Q5-Q1, but its q25 PR delta is lower than the clean V1 control by about 0.00501.

### Adjudication

This is **fatal to the old interpretation that V2 clearly solved V1 by improving lower-tail PR robustness**. It is not fatal to V2 as the selected candidate inside the frozen V2 candidate set.

The correct historical statement is:

> V2 is the selected clean contextual V2 architecture and shows stronger median ROC and Q5-Q1 plus a small median PR improvement, while incremental lower-tail PR superiority over V1 is not established.

Do not rerun or tune V2 to restore the old q25 story.

## 4. V1 was non-champion-eligible — `GOVERNANCE_LIMITATION_FOR_SUCCESSOR_CLAIMS`

### Attack

The frozen V2 process legitimately used V1_HGB_CONTROL as a non-eligible control, so the official selection answers which eligible V2 candidate wins rather than whether any V2 candidate robustly dominates V1.

### Adjudication

This was valid governance for the experiment that was actually specified. It becomes a problem only when interpreting `V2 selected` as `V2 proved superior to V1`.

Future successor experiments should keep the incumbent parent/control explicitly eligible or define a preregistered paired superiority/non-inferiority gate against it. A new challenger should not be promoted merely because it wins among new variants while the incumbent cannot win.

The historical V2 verdict remains frozen and unchanged.

## 5. Row-pooled metrics versus daily decision unit — `MUST_CHANGE_EVALUATION_PROTOCOL`

### Attack

PR/ROC use pooled validation rows, and within-date Q buckets are subsequently summarized by pooled rows. Dates with more resolved eligible names therefore carry more weight than dates with fewer names.

### Adjudication

**Material evaluation mismatch, but repairable prospectively.** The product decision is naturally one cross-sectional ranking event per trading session, so a future primary evaluator should give explicit status to date-level performance rather than letting row count silently define date weights.

Future contract should include, before outcome access:

- equal-date or otherwise explicitly justified date weighting;
- date-level top-tail/bottom-tail diagnostics;
- paired challenger-minus-control daily metrics where feasible;
- pooled-row PR/ROC retained only as complementary diagnostics, not the only primary view.

Do not recompute a new Stage-4 V2 verdict from consumed historical outcomes merely to rescue this issue.

## 6. Future-resolution composition interacting with date weighting — `MUST_CHANGE_TARGET_OR_POPULATION_CONTRACT`

### Attack

The number of model/evaluation rows on a date depends partly on future barrier resolution, which itself can vary with volatility, liquidity and regime.

### Adjudication

This is not ordinary leakage. It is a **selection/estimand problem coupled to evaluation weighting** and therefore belongs with the resolved-only target issue rather than being a cosmetic metric fix.

Simply equal-weighting dates while still training only on future-resolved rows would not fully repair it. A future generation should define eligibility at decision time and explicitly encode later non-resolution rather than let future resolution determine whether an observation exists.

## 7. Market context as possible era fingerprint — `OPEN_HYPOTHESIS_MANAGEABLE`

### Attack

`market_primary_liquid_count` and other broad-market variables may partly identify historical eras, especially under a fixed nominal liquidity threshold and expanding listing universe.

### Adjudication

Concern is legitimate but **not demonstrated as a defect**. Market context is economically meaningful and its inclusion is a central V2 lesson. Removing it merely because it correlates with time could destroy useful causal state information.

Future handling should be bounded and outcome-blind where possible:

- measure time drift and universe-composition drift in candidate context variables;
- avoid explicit calendar-age proxies unless economically motivated;
- require stable, reproducible universe construction;
- if a feature is nearly deterministic of calendar era, treat that as a preregistration/design concern before outcome comparison.

No post-hoc V2 feature-importance mining is warranted.

## 8. Ranking-native objective question — `OPEN_ARCHITECTURE_QUESTION`

### Attack

The frozen pairwise challenger was linear, XS-only and bounded; it did not test a nonlinear market-context-conditioned ranking objective.

### Adjudication

The old pairwise result should not be generalized to `ranking objectives do not work`. This is **unknown**, not evidence that V2 is defective.

If a future clean-generation study revisits the learning objective, the fair test is same support, same causal information set and frozen comparable complexity between:

- a contextual pointwise learner;
- a contextual ranking/group-aware learner.

This must be a small preregistered candidate family, not a broad hyperparameter/model search.

## 9. Market-relative signal may contain sector exposure — `MANAGEABLE_PRODUCT_CHOICE_NOT_FATAL`

### Attack

Broad-market-relative strength can embed sector rotation because no PIT-safe historical sector-relative control was available.

### Adjudication

Not automatically a flaw. Sector exposure can itself be economically useful if the product is allowed to capture sector rotation. It becomes a confound only if the intended estimand is stock-specific alpha independent of sector.

Future design should decide explicitly whether sector exposure is:

- allowed alpha;
- controlled risk;
- or a separate state/sidecar.

PIT sector data must be defensible before any historical neutralization is introduced. Current data limitations mean this remains an open design dimension, not a reason to reject V2.

## 10. Representation redundancy / raw reconstruction — `SECONDARY_NOT_FATAL`

### Attack

Several V2 market-relative features plus market medians reconstruct the raw stock variable, and some structure variables are algebraically redundant.

### Adjudication

This weakens causal interpretability of the phrase `normalization solved transportability`, but redundancy is not inherently invalid for tree learners. Multiple threshold-friendly views can improve learning stability.

Future representation should prefer economically distinct, minimally redundant states when possible, but should not impose orthogonality for its own sake. The scientific claim must match what is actually tested: hybrid contextual representation, not pure normalization.

## 11. Changing peer set sensitivity — `MANAGEABLE_DATA_CONTRACT_DEPENDENCY`

### Attack

Percentile ranks and market medians depend on the same-date peer set. IPOs, suspensions, liquidity-threshold crossings and upstream identity errors can change peers' features.

### Adjudication

This is partly the intended meaning of cross-sectional ranking, not an error. It does raise the required quality bar for the entire universe pipeline.

Future clean-generation usage should require:

- PIT listing/security intervals;
- explicit activity/no-trade semantics;
- exact same-date universe reconstruction;
- fail-closed coverage/integrity checks;
- feature provenance that records peer-universe definition.

The PIT reconstruction showing propagation from a small upstream listing correction is evidence that these guards matter.

## 12. Fixed nominal IDR 1bn liquidity threshold — `MANAGEABLE_BUT_REOPEN_FOR_EXECUTION`

### Attack

A fixed nominal threshold is not temporally scale-neutral and may be too permissive for an eventual executable portfolio.

### Adjudication

Not a reason to reject V2's historical research universe. It is a reason not to equate that universe with the eventual tradable universe.

A future product-stage contract should separate:

- broad research eligibility;
- model scoring eligibility;
- executable/capacity eligibility.

Any revised liquidity rule must remain strictly PIT and should be frozen before performance comparison. No threshold optimization on consumed history.

## 13. Six folds are correlated development evidence — `INTERPRETATION_LIMITATION`

### Attack

Expanding folds share training history and adjacent market regimes; candidate design itself was informed by consumed historical development knowledge.

### Adjudication

Correct. `6/6 positive` is evidence of historical-development consistency, not six independent replications. This does not invalidate the folds; they remain substantially better than random splitting.

The correct remedy is genuinely fresh prospective validation, not additional slicing/mining of the same historical period. Historical rows through 2026-07-31 remain development knowledge.

## 14. No turnover/capacity/portfolio utility — `OUT_OF_SCOPE_FOR_V2_BUT_REQUIRED_BEFORE_DEPLOYMENT`

### Attack

PR/ROC/Q5-Q1 do not establish an economically tradable portfolio.

### Adjudication

This was intentionally outside V2's signal-research scope and therefore is not an implementation defect. It becomes mandatory only after a signal survives the new target/execution and prospective-validation gates.

Do not contaminate early alpha research by optimizing execution/PnL on the same historical outcomes. Execution, turnover, capacity and portfolio construction should be a later separately frozen layer.

## 15. No time-aware uncertainty around small incremental V2-vs-V1 edge — `IMPORTANT_NOT_FATAL`

### Attack

The clean median PR difference over V1 is about +0.001085 and no block/time-aware uncertainty statement accompanies that incremental effect.

### Adjudication

Important for claims of small superiority, but it would not rescue the deeper target/execution problems. Future comparisons should preregister time-aware uncertainty/robustness summaries that respect date dependence, for example block-based or date-level paired summaries where appropriate.

Do not treat a retroactive interval estimated after seeing the consumed V2 outcomes as a new promotion gate.

## Final criticality ranking

### P0 — must be reopened before any next-generation model is called economically aligned

1. decision population / resolved-only conditioning;
2. executable entry/reference semantics.

### P1 — must be fixed in the next experimental governance/evaluator

3. incumbent parent must be able to win or have an explicit paired non-inferiority/superiority gate;
4. date-level decision weighting must be explicit;
5. target/population design must prevent future resolution from silently determining sample existence;
6. historical development must remain distinct from fresh prospective confirmation.

### P2 — explicit candidate/design decisions, not automatic fixes

7. contextual pointwise versus contextual ranking objective;
8. sector exposure policy when PIT sector history becomes defensible;
9. market-context/era-drift guardrails;
10. research versus execution liquidity universe.

### P3 — engineering/scientific hardening

11. cross-sectional peer-universe integrity and provenance;
12. representation redundancy/interpretation control;
13. time-aware uncertainty for small paired effects;
14. later turnover/capacity/portfolio utility layer.

The clean q25 reversal is not itself a future architecture requirement; it is an evidence constraint: any documentation must stop claiming that V2 clearly established lower-tail robustness superiority over V1.

## Inheritance rules for a future clean-generation ranker

### Retain from V2

- PIT and fail-closed causal data discipline;
- same-date cross-sectional framing as a valid design principle;
- explicit continuous market context;
- stock-relative-to-market representation where economically justified;
- exact common-support paired comparisons;
- chronological validation with purge/maturity gaps;
- worst-fold/top-tail diagnostics alongside aggregate discrimination;
- frozen pre-outcome candidate families;
- no-rescue/no-retune after a gate failure;
- Clean V2 as an important benchmark/control.

### Do not inherit automatically

- H10 TP-first-versus-SL-first resolved-only estimand;
- Close_t as economic entry reference;
- all 25 exact V2 columns;
- HGB as mandatory learner;
- exact 20/60 lookbacks;
- row-pooled metrics as the sole primary evaluator;
- V2's fixed nominal liquidity rule as the execution universe;
- the claim that the old pairwise result settles ranking-vs-pointwise learning;
- the claim that V2 proved robust incremental superiority over V1.

## Minimum governance contract for the next clean-generation experiment

Before any new outcome run, the future specification should at minimum freeze:

1. decision timestamp and earliest executable entry reference;
2. decision-time eligible population, including treatment of non-hit/abstention outcomes;
3. target/utility semantics independent of future sample inclusion;
4. primary date-level evaluation unit and complementary pooled metrics;
5. incumbent Clean V2 comparator with explicit paired promotion rule;
6. candidate information sets and model/objective families before outcome inspection;
7. exact common-support rules and peer-universe provenance;
8. development boundary versus genuinely fresh prospective validation boundary;
9. explicit separation of signal research from later execution/portfolio validation.

This is a governance template only. It does not authorize a new model, new target, historical rerun, fresh-forward outcome access, or V2 rescue.

## Stage-4 verdict

`V2_RETAIN_AS_CLEAN_CONTEXTUAL_BENCHMARK_REOPEN_TARGET_EXECUTION_AND_SUCCESSOR_GOVERNANCE`

The red-team does not justify throwing V2 away. It does justify narrowing the claim substantially. The strongest durable V2 contribution is contextual representation plus disciplined historical comparison. The two pieces that should **not** anchor the next generation are its resolved-only barrier estimand and its Close_t execution/reference semantics. The next generation should also make the incumbent able to win, evaluate the product at an explicit date-level decision unit, and reserve final confirmation for truly fresh prospective data.

Stop here for Ranking V2 forensic audit. No V2 rescue or new outcome experiment is authorized. A separate next stage may begin forensic reconstruction of Ranking V3 only after an explicit user instruction.
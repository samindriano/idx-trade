# Ranking V2 Forensic Audit — V2-A / V2-B / V2-D Rejected-Candidate Review

Date: 2026-08-16 (Asia/Jakarta)
Status: `FORENSIC_A_B_D_RECORDED_NO_EXPERIMENT`
Branch: `research/idx-ranking-v1-forensic-audit-v1`

## Scope

Documentation-only forensic review of the three non-champion Ranking V2 candidates:

- V2-A `LOGISTIC_XS`;
- V2-B `HGB_XS`;
- V2-D `PAIRWISE_LOGISTIC_XS`.

No model fitting, outcome rerun, provider call, protected/fresh-forward outcome access, hyperparameter search, feature-importance mining, rescue, threshold search, or canonical-model mutation was performed.

The current trusted numerical evidence is the corrected PIT-safe replay, not the original contaminated fitted-model lineage. Original V2 results are retained only as historical-reference evidence when useful for stability comparison.

## Frozen candidate matrix

All three candidates use the same ten within-date XS percentile-rank stock features. Their main architectural differences are:

| candidate | information set | learner/objective | key training behavior |
|---|---|---|---|
| V2-A `LOGISTIC_XS` | 10 XS ranks | pointwise logistic | median imputation + missing indicators + standardization |
| V2-B `HGB_XS` | 10 XS ranks | pointwise HistGradientBoosting | median imputation + missing indicators; frozen V1 HGB settings |
| V2-D `PAIRWISE_LOGISTIC_XS` | 10 XS ranks | same-date pairwise logistic utility | item-level median imputation + scaling, <=256 positive-negative pairs/date, symmetric ordered differences |

V2-C `HGB_XS_MARKET` is not re-audited here; it was separately reviewed as the clean contextual benchmark.

The design gives a useful but incomplete experimental grid:

| | pointwise | pairwise |
|---|---|---|
| linear, XS-only | V2-A | V2-D |
| nonlinear, XS-only | V2-B | **not tested** |
| nonlinear + market/context | V2-C | **not tested** |

Therefore no historical V2 result closes the question of a nonlinear/context-conditioned ranking-native objective.

## Current clean replay evidence

Corrected PIT-safe replay aggregate:

| candidate | median PR delta | q25 PR delta | positive PR folds | median ROC | ROC > .50 folds | median Q5-Q1 |
|---|---:|---:|---:|---:|---:|---:|
| V1 control | 0.02310942 | 0.01766978 | 6/6 | 0.51829043 | 5/6 | 0.03002639 |
| V2-A `LOGISTIC_XS` | 0.00931842 | 0.00507168 | 6/6 | 0.50613126 | 5/6 | 0.01925865 |
| V2-B `HGB_XS` | 0.01829351 | 0.01582069 | 6/6 | 0.51539832 | 6/6 | 0.04153618 |
| V2-C `HGB_XS_MARKET` | 0.02419450 | 0.01265903 | 6/6 | 0.52517063 | 5/6 | 0.05308354 |
| V2-D `PAIRWISE_LOGISTIC_XS` | 0.01071192 | 0.00922985 | 6/6 | 0.50832195 | 6/6 | 0.02475658 |

All A/B/D were historically eligible under the frozen V2 gate. Calling them simply “failed models” is therefore misleading: they failed to become champion, not the absolute candidate-eligibility gate.

---

# V2-A — `LOGISTIC_XS`

## What A actually tested

A was the low-capacity test of whether the ten same-date percentile-rank stock states contain approximately additive/linear ranking information without explicit market state.

Frozen implementation:

- features: only the ten `xs_rank_*` columns;
- training-only median imputation with missing indicators;
- StandardScaler fit only on training rows;
- LogisticRegression `C=1`, `lbfgs`, `max_iter=1000`, seed 42;
- no tuning.

Because the predictors are percentile ranks, a linear logistic model effectively asks whether one monotonic additive utility over those ranks is enough. It cannot naturally express threshold effects, U-shapes, or feature interactions unless those shapes were already engineered into the input columns.

## What the result proves

Clean A is weak but not null:

- median PR delta `+0.00931842`;
- q25 `+0.00507168`;
- positive PR delta `6/6` folds;
- median ROC `0.50613126`;
- median Q5-Q1 `+0.01925865`.

Thus the XS representation carries some historical ordering information even under a deliberately simple linear learner. The signal is not solely an HGB artifact.

## What A does not prove

A's loss to B/C does **not** prove logistic regression is generally unsuitable for IDX ranking. It proves the exact additive-linear utility over the ten frozen XS ranks was materially weaker than the frozen nonlinear alternatives.

Possible explanations such as nonlinear thresholds or interactions are strongly plausible but remain mechanism hypotheses; the outcome comparison alone does not identify which relation generated the gain.

## A versus B: strongest clean isolation of nonlinear capacity

A and B use the same ten XS source features and both are pointwise binary learners. Clean B minus A:

- median PR delta: `+0.00897509`;
- q25 PR delta: `+0.01074901`;
- median ROC: `+0.00926706`;
- median Q5-Q1: `+0.02227753`.

This is much larger than the clean C-versus-V1 median PR increment. It is strong historical evidence that **model capacity/nonlinear interaction handling mattered materially inside the XS-only representation**.

Caveat: the learners are not identical except for linearity — logistic is standardized and HGB is a tree ensemble — so this is architecture evidence rather than a formal causal decomposition of “nonlinearity” alone.

## A verdict

`V2_A_POSITIVE_LOW_CAPACITY_SANITY_CONTROL_NOT_ARCHITECTURAL_PARENT`

Retain A's lesson: a simple model should remain available as a low-capacity sanity comparator in future work. Do not rescue A by adding transformations post hoc to consumed V2 outcomes.

---

# V2-B — `HGB_XS`

## Why B is more important than its loser status suggests

B is the cleanest V2 ablation for asking what happens when the model has nonlinear capacity but sees **only relative stock state**, with no explicit market-state / stock-minus-market package.

Frozen implementation:

- same ten XS percentile ranks as A;
- exact frozen V1 HGB settings: learning rate .05, 200 iterations, 31 leaves, L2=1, seed 42;
- no market context;
- no stock-minus-market features;
- no Open, sector, foreign flow, fundamentals, or other information class.

Because C uses the same HGB settings and adds the 15 context/relative columns, B is the most useful historical control for the V2 context package.

## B was actually a strong candidate

Clean B:

- median PR delta `+0.01829351`;
- q25 `+0.01582069`;
- positive PR `6/6`;
- median ROC `0.51539832`;
- ROC > .50 `6/6`;
- median Q5-Q1 `+0.04153618`.

Among champion-eligible V2 candidates, B has the **best clean q25 PR delta**. C has the higher median PR, ROC and Q5-Q1, but B's q25 is higher by `0.00316166`.

This matters because the original V2 narrative framed C's advantage mainly as robustness. Under clean lineage, the context package produces a trade-off rather than uniform domination.

## B versus C: what market/context appears to do

Clean C minus B:

- median PR delta: `+0.00590099`;
- q25 PR delta: **`-0.00316166`**;
- median ROC: `+0.00977231`;
- median Q5-Q1: `+0.01154736`.

Therefore the clean historical evidence supports:

- context materially improves typical pooled discrimination;
- context materially improves broad ROC ordering;
- context improves extreme top-vs-bottom separation;
- but context does **not** improve lower-quartile PR robustness versus B.

So the strongest defensible lesson is not “market context stabilizes every regime.” It is:

> explicit market/relative context changes the ranking geometry beneficially on several aggregate/tail metrics, but the gain is heterogeneous across folds.

Also, C adds a bundled 15-column package. Six market-relative features plus corresponding market medians can reconstruct raw stock values. Therefore B→C does not isolate “market regime variables” alone; it isolates the full hybrid context/absolute-reconstruction package.

## B versus V1: pure XS normalization is not enough

Clean B minus clean V1 control:

- median PR delta: `-0.00481591`;
- q25: `-0.00184909`;
- median ROC: `-0.00289211`;
- median Q5-Q1: **`+0.01150979`**.

This combination is informative. B loses broad PR/ROC discrimination versus V1 raw-HGB, while improving Q5-Q1.

A plausible reading is that percentile ranks preserve relative tail ordering but discard absolute magnitude information useful for broader discrimination. That mechanism is not directly proven, but it fits the fact that C recovers raw/relative/context views and then improves median/ROC/Q5-Q1.

## B verdict

`V2_B_STRONG_XS_NONLINEAR_ABLATION_RETAIN_AS_KEY_REPRESENTATION_EVIDENCE`

B should not be treated as an irrelevant loser. Its main scientific contribution is showing:

1. nonlinear XS-only state is materially stronger than linear XS-only state;
2. XS-only HGB is still not a clear replacement for the raw V1 control;
3. the C context package adds substantial median/ROC/tail value, but not uniform q25 robustness.

No B rescue is authorized.

---

# V2-D — `PAIRWISE_LOGISTIC_XS`

## Exact pairwise construction

D is more specific than “a ranking model.” It uses:

- the same ten XS item features;
- training-item median imputation and StandardScaler;
- for each training date, resolved positive and negative items only;
- Cartesian positive-negative pairs;
- maximum 256 unique pairs per date;
- deterministic date-derived RNG when the Cartesian set exceeds 256;
- every selected pair contributes both `x_pos-x_neg -> 1` and `x_neg-x_pos -> 0`;
- final logistic model `C=1`, `lbfgs`, 1000 iterations, seed 42;
- validation score is item-level learned utility.

Thus D is best understood as a bounded linear same-date utility-ranking test, not a general ranking-learning verdict.

## D's absolute result is also positive

Clean D:

- median PR delta `+0.01071192`;
- q25 `+0.00922985`;
- positive PR `6/6`;
- median ROC `0.50832195`;
- ROC > .50 `6/6`;
- median Q5-Q1 `+0.02475658`.

It therefore passed the V2 eligibility gate. It did not “fail to find signal”; it lost to higher-performing candidates.

## D versus A: there is modest positive evidence for pairwise framing

Clean D minus A:

- median PR delta `+0.00139350`;
- q25 `+0.00415817`;
- median ROC `+0.00219069`;
- median Q5-Q1 `+0.00549793`.

The direction is consistently favorable to D in these aggregate diagnostics, particularly q25 and Q5-Q1. So the historical evidence does **not** say “pairwise was useless.” It says the exact pairwise-linear construction modestly improved over the pointwise-linear XS comparator.

## But A→D is not a pure objective experiment

There are at least three confounds:

1. **training weighting changes**: D caps positive-negative pairs at 256 per date, making high-opportunity dates contribute a bounded number of pairs rather than simply contributing all their item rows;
2. **sample representation changes**: pairwise examples are symmetric differences, not item rows;
3. **preprocessing differs slightly**: A's pointwise preprocessor adds missing-value indicators, while D's item-level imputer does not add missing indicators.

Therefore D's gain over A cannot be attributed solely to “ranking loss.” It may partly arise from date balancing, pair construction, or preprocessing differences.

This weighting distinction is especially interesting given the later V2 forensic finding that ordinary pointwise evaluation/training is row-centric while the product is date-centric. D accidentally moves training somewhat closer to bounded per-date contribution, although its final validation metrics are still evaluated under the common V2 evaluator.

## D versus B: nonlinear capacity dominates this simple pairwise gain

Clean D minus B:

- median PR delta `-0.00758159`;
- q25 `-0.00659084`;
- median ROC `-0.00707637`;
- median Q5-Q1 `-0.01677960`.

So in the tested grid, moving from linear pointwise A to linear pairwise D helps modestly, but moving from linear pointwise A to nonlinear pointwise B helps far more.

That does **not** imply pointwise objectives are intrinsically superior. The crucial missing cells are:

- nonlinear XS pairwise/ranking;
- nonlinear contextual ranking using the information set that made C strongest.

Furthermore, same-date market constants cancel in naive pair differences. A future contextual ranking architecture would need market-conditioned utility/interactions or a group-aware learner; simply appending identical daily market columns to `x_pos-x_neg` would not preserve their direct effect.

## D still inherits every V1/V2 P0 target problem

Pairwise learning does not repair:

- resolved-only future-conditioned sample inclusion;
- H10 TP-first/SL-first estimand;
- Close_t barrier reference despite after-close information timestamp;
- absence of realistic t+1 executable entry semantics.

It merely changes how the same resolved labels are learned.

## D verdict

`V2_D_MODEST_PAIRWISE_EVIDENCE_OBJECTIVE_QUESTION_REMAINS_OPEN`

Retain the lesson that ranking-aware/group-aware objectives remain worth a fair future test. Do not interpret D's non-champion result as evidence against ranking-native learning, and do not rerun D variants on consumed history.

---

# Cross-candidate decomposition

The useful decomposition of V2 is:

### A -> B

Same XS information; pointwise logistic -> pointwise HGB.

Observed change is large and positive. Main lesson: nonlinear capacity/interactions matter materially for the frozen XS representation.

### A -> D

Same headline XS information; pointwise linear -> bounded pairwise linear.

Observed change is modest and positive, but objective is confounded with date-pair weighting and preprocessing differences. Main lesson: ranking-native framing is **not falsified** and may help, but V2-D is not a definitive test.

### B -> C

Same HGB settings; XS-only -> XS + market-state + stock-relative package.

Observed clean change improves median PR, ROC, and Q5-Q1 materially, while q25 PR becomes worse. Main lesson: context package adds useful information/representation, but not uniformly robust improvement.

## Scientific ranking of the three non-champions

1. **V2-B — highest forensic value.** Best isolation of nonlinear XS and the necessary baseline for interpreting C's context package.
2. **V2-D — high forensic value.** Shows modest benefit over A and exposes that the ranking-objective question remains unresolved.
3. **V2-A — useful control.** Demonstrates that XS signal is present even under a low-capacity additive learner and anchors A->B / A->D comparisons.

## What should be inherited into future clean-generation design

Retain as principles:

- include a deliberately simple low-capacity comparator like A;
- if comparing objectives, hold information set/model capacity/preprocessing/date weighting as equal as possible;
- preserve a nonlinear stock-state comparator because B shows major value from nonlinear capacity;
- treat contextual representation and ranking objective as separate axes;
- make date/group weighting explicit instead of letting sampling choices silently alter it;
- keep incumbent Clean V2 able to win under a preregistered paired gate.

Do not automatically inherit:

- logistic or HGB as mandatory learners;
- the exact ten XS columns;
- pair budget 256;
- the exact pairwise logistic construction;
- the resolved-only H10 target or Close_t execution semantics;
- the interpretation that market context universally improves robustness.

## Final verdict

`V2_A_B_D_CLOSED_AS_INFORMATIVE_NONCHAMPION_ABLATIONS`

The rejected V2 candidates are scientifically useful. A establishes small linear XS signal; B shows a much larger nonlinear XS effect and reveals that C's context advantage is heterogeneous; D gives modest evidence that pairwise/group-aware learning may help but does not fairly settle pointwise versus ranking-native objectives. No candidate should be rescued or rerun on consumed V2 history.

With this checkpoint, the Ranking V2 candidate family is considered forensically complete enough to move to V3 when explicitly instructed.
# Ranking V3 Forensic Audit — Hypothesis Ladder, Clean-Lineage Reversal, and Design Lessons

Date: 2026-08-16 (Asia/Jakarta)
Status: `FORENSIC_REVIEW_ONLY_NO_NEW_EXPERIMENT`
Branch: `research/idx-ranking-v1-forensic-audit-v1`

## Scope

Documentation-only forensic reconstruction of Ranking V3. No model fitting, provider call, historical outcome rerun, fresh-forward/protected outcome access, feature-importance mining, hyperparameter search, rescue, threshold search, or canonical-model mutation was performed.

This checkpoint distinguishes:

1. the original 2026-08-10 V3 historical-development ladder;
2. later-discovered PIT/training-lineage contamination in the shared historical data lineage;
3. the accepted PIT-safe replay result for V2/V3-B/O2 on 2026-08-13;
4. scientific lessons that remain useful without treating legacy contaminated fitted results as clean canonical evidence.

The current clean historical parent remains V2 `HGB_XS_MARKET`. V3-B is not a clean promoted parent.

---

# 1. What V3 was

V3 was a bounded hypothesis ladder around the exact V2 `HGB_XS_MARKET` control, not a broad feature/model tournament.

The principal branches were:

- V3-A Recency: change training-row temporal weights only;
- V3-B Structure-Lite: append one preregistered 8-feature causal support/resistance geometry block;
- V3-C Regime specialization: route each date to NORMAL/STRESS HGB experts;
- V3-D Sector-relative: preregistered but blocked before outcomes because PIT sector history was not defensible;
- V3-E True Ranking: replace binary HGB with one grouped same-date LambdaMART candidate on the exact V2 25-feature information set.

All of these retained the inherited V1/V2 H10 resolved-only first-touch target, `Close_t` label reference, primary-liquid universe, and after-close information semantics. Therefore V3 did not repair the previously identified P0 target/estimand or executable-entry mismatch.

Original V3 experiments used the old V2 prepared table SHA `522f17...`. The later accepted PIT-safe reconstruction uses corrected V2 table SHA `79d33b...`. Only V2/V3-B/O2 received the accepted clean replay; V3-A, V3-C and V3-E were not replayed on corrected inputs and must not be upgraded to clean-lineage evidence.

---

# 2. V3-A Recency

## Exact hypothesis

V3-A kept the exact V2 rows, 25 features, HGB estimator, target, folds and evaluator. Only training sample weights changed.

Frozen challengers:

- `HL252`: exponential half-life 252 official sessions;
- `HL504`: exponential half-life 504 official sessions.

Weights were normalized within each fold to mean one, preserving total sample-weight scale. Discovery used V2F1-V2F4 only.

## Legacy result

Both challengers passed absolute sanity but failed the paired promotion gate.

`HL252` paired aggregate:

- median PR improvement `-0.00015116`;
- q25 `-0.00695694`;
- worst `-0.00919292`;
- PR non-below control `2/4`;
- median ROC change `-0.00383331`.

`HL504`:

- median PR improvement `+0.00005686`;
- q25 `-0.00997348`;
- worst `-0.03453010`;
- PR non-below control `2/4`;
- median ROC change `-0.00168551`.

Verdict was `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`.

## What it supports

Under the tested fixed half-lives, downweighting old observations did not improve robust paired performance. More recent data is not automatically better, and the older history appears to carry useful signal under the V2 representation.

## What it does not prove

It does not prove drift is absent or that every recency method is harmful. It tests exactly two smooth exponential weighting rules on the contaminated legacy prepared-table lineage. It does not test state-conditioned adaptation, online updating, change-point methods, or a new target.

Because V3-A was not clean-replayed, its result remains legacy historical reference rather than accepted clean evidence. No old-history recency rescue is authorized.

---

# 3. V3-B Structure-Lite

## Exact information added

V3-B was a real new technical-information representation, not a monotonic transform of V2 columns. It appended eight causal geometry features to the exact V2 25-feature control:

1. `structure_support_distance_atr`;
2. `structure_resistance_distance_atr`;
3. `structure_support_touch_count_60`;
4. `structure_resistance_touch_count_60`;
5. `structure_nearest_level_age_sessions`;
6. `structure_role_reversal_count_120`;
7. `structure_breakout_retest_state`;
8. `structure_breakout_volume_confirmed`.

Key frozen construction choices included:

- trailing left-only 5-session pivots;
- 60-session level candidate window;
- support/resistance clustering at `0.5 * max(ATR_p, ATR_q)`;
- 60-session OHLC touch counts with minimum three-session separation;
- 120-session role-reversal history;
- 10-session retest horizon;
- breakout-volume confirmation at `1.5x` trailing-20 median volume with at least 10 observations.

Current session t was prohibited from creating the historical level inventory but could be used for after-close distance and breakout/retest state.

This was a disciplined attempt to salvage support/resistance concepts from an older legacy project while explicitly removing centered/future-confirmed pivots, outcome-conditioned boosts, hand scoring and empirical probability layers.

## Original result

Original F1-F4 discovery passed cleanly under the then-used lineage:

- paired PR improvements: `+0.007948`, `+0.001841`, `+0.004879`, `+0.002973`;
- median `+0.00392585`;
- q25 `+0.00268979`;
- worst `+0.00184130`;
- PR non-below `4/4`;
- median ROC change `+0.00224592`;
- median Q5-Q1 change `+0.01132415`.

The one-shot original late V2F5/V2F6 confirmation also passed:

- F5 PR improvement `+0.00166614`;
- F6 `+0.01351612`;
- median `+0.00759113`;
- both late Q5-Q1 changes positive.

This produced the old historical-development `V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS` and final V3-B identity.

## Accepted PIT-safe replay changes the decision

The later corrected replay used 292,631 rows / 737 tickers and exact frozen V3-B semantics. Paired Structure-Lite minus clean V2 control changes were:

| Fold | PR change | ROC change | Q5-Q1 change |
|---|---:|---:|---:|
| V2F1 | +0.00790704 | +0.00259663 | +0.01396779 |
| V2F2 | +0.00272251 | +0.00330468 | +0.01930785 |
| V2F3 | -0.00116421 | -0.00105720 | -0.00860860 |
| V2F4 | +0.01454598 | +0.01342507 | +0.02505553 |
| V2F5 | **-0.01309503** | -0.00753950 | **-0.01727346** |
| V2F6 | +0.01692841 | +0.01639913 | -0.00396765 |

The clean F1-F4 discovery pattern would still satisfy the old paired discovery gate: median PR change about `+0.005315`, q25 about `+0.001751`, worst `-0.001164`, nonnegative `3/4`, with positive median ROC and Q5-Q1 changes.

The failure is specifically the one-shot late confirmation: V2F5 becomes materially inferior. The accepted replay verdict is:

`V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`.

This is a new result on corrected inputs, not reinterpretation of the legacy result. Old V3-B fitted models are `LEGACY_CONTAMINATED_REFERENCE` only.

## What B still teaches

There is credible historical evidence that causal support/resistance geometry can alter the ranking usefully: the discovery benefit broadly survives the PIT repair. But it did not demonstrate sufficient late-period transportability under the frozen gate.

The most important lesson is therefore not "support/resistance works"; it is:

> a carefully causal geometry representation produced repeatable development-fold signal, but its incremental edge was fragile enough that a small lineage correction reversed the late promotion decision.

## B pen-test findings

### B1. Causal but partly retrospective pattern semantics

At decision time t, all data used are historical/current and therefore causal. However the current 60-session level cluster is constructed using the whole prior window and then historical touches are counted against that currently inferred level, including interactions earlier than the newest pivot that helped define the cluster. This is not future leakage relative to t, but it is retrospective pattern reconstruction. The feature should be interpreted as "pattern recognizable at t", not as a level that market participants necessarily knew throughout the entire touch history.

### B2. Trailing pivot is not a classical swing pivot

A high pivot is simply a high equal to the maximum of its trailing five sessions; low pivot is symmetric. In a persistent trend, consecutive/new highs can repeatedly qualify. The clustering/touch machinery may therefore encode trend/extrema persistence as much as classical support/resistance. The economic mechanism is plausible but not identified by the outcome test.

### B3. Fixed geometry constants are hand-designed priors

The 5/60/120/10 windows, 0.5 ATR cluster/touch width, 1% price floor and 1.5x volume rule were preregistered and not outcome-tuned, which is good governance. But preregistration does not prove these constants are economically invariant across ticker price scales, liquidity regimes or volatility states.

### B4. Role-reversal count conflates opportunity count and success

`structure_role_reversal_count_120` sums completed reversals across all current clusters but the number of available clusters is deliberately not exposed as a feature. A larger count can mean more successful reversals, simply more candidate levels, or both. The representation does not separate denominator from event rate.

### B5. Split/corporate-action semantics are a material data threat

Structure-Lite depends on 60/120-session level geometry and ATR. A later corporate-actions audit found the historical price provider/panel is not demonstrated to be uniformly exchange-unadjusted or uniformly split-adjusted around official stock-split events. Only 1/39 bounded official split events showed the expected nearby mechanical OHLC transition, and that one transition was five observed sessions earlier than the official effective schedule. This does not prove V3-B results were driven by splits, but it means the specification's assumed split-consistent technical-price frame was not independently established for the whole history. Level geometry is more exposed to this issue than simple short-horizon return ranks.

### B6. The clean-gate reversal is a robustness warning

The PIT-safe correction removed invalid KOCI-derived lineage and changed same-date feature/context construction. The fact that V3-B changes from late PASS to late FAIL, despite unchanged code/model/gates, shows the incremental edge was not far from the decision boundary. This is evidence of brittleness, not proof the feature family has zero signal.

---

# 4. V3-C Regime Specialization

## Exact design

V3-C used three causal market-context series already present in V2:

- 20-session positive breadth;
- median 20-session return;
- median ATR/Close.

For each date, prior-252-session quantiles defined stress votes: breadth <= q25, return <= q25, ATR/Close >= q75. `STRESS` required at least 2/3 votes. Separate exact V2 HGB experts were fit for NORMAL and STRESS; all securities on a date used the same expert.

## Legacy result

Overall paired PR changes were:

- F1 `-0.01111864`;
- F2 `-0.02214287`;
- F3 `+0.02220754`;
- F4 `-0.01351574`.

Median `-0.01231719`, q25 `-0.01567253`, non-below `1/4`; median Q5-Q1 change `-0.02075393`, non-below `0/4`.

STRESS was especially poor: median paired PR `-0.02896467` and median Q5-Q1 `-0.03574684`.

Verdict: `V3_C_REGIME_KILL_KEEP_V2_CONTROL`.

## Important confounds

### C1. It is not a pure specialization test because warmup rows are discarded

The candidate excludes `MISSING_WARMUP` rows from expert training while the global control uses them. The fixed discarded block is 28,124 rows / 127 dates. That equals approximately:

- 24.6% of F1 training rows;
- 19.9% of F2;
- 16.9% of F3;
- 14.7% of F4.

Therefore C changes both specialization and effective training history. Some degradation could come from lost early data rather than the two-expert idea itself.

### C2. Pooled PR/ROC can be affected by expert score-scale differences

NORMAL and STRESS HGBs are independently fit. The spec intentionally forbids cross-expert score alignment. This is clean for the frozen hypothesis, and within any date every stock uses one expert, so within-date ordering is unaffected by between-expert scale. But pooled fold PR-AUC/ROC compares scores across dates/regimes and can be harmed by arbitrary expert score scales.

This cannot fully explain failure because Q5-Q1, which is within-date, was also worse in every fold versus control. It does mean the large pooled PR penalty should not be attributed solely to poor same-date ranking.

### C3. Hard routing throws away useful shared structure

V2 already let one nonlinear HGB condition continuously on market-state variables. V3-C replaces that with data fragmentation into two disjoint experts while keeping the same feature set. The negative result is consistent with the global model benefiting from pooled information plus continuous context rather than hard specialization.

## Status

V3-C was not replayed on corrected PIT-safe inputs, so its numbers remain legacy contaminated-reference evidence. Given the large old paired failure, this audit records the lesson but does not authorize a rescue/replay.

---

# 5. V3-D Sector Relative

V3-D never consumed model outcomes. The historical sector map failed the point-in-time data gate, and the project correctly refused current-sector backfill or invented effective/publication dates.

It is `PARKED`, not failed.

Current 2026-08-16 coordination still records PIT sector history as parked with `5 ready / 3 blocked`; 2023 is near-resolved but official bytes remain unavailable and dependent modeling remains prohibited.

Therefore there is no scientific performance claim for V3-D in either direction. Any statement that sector relative "failed" would be false.

---

# 6. V3-E True Ranking / LambdaMART

## Exact design

V3-E was a materially fairer ranking-objective test than V2-D:

- exact same 25 V2 features;
- exact same rows/folds;
- same training-only median imputer + missing indicators;
- one query per signal date;
- XGBRanker with `rank:ndcg`;
- binary 0/1 relevance labels retained;
- 200 trees, learning rate .05, max depth 5, lambda 1, full row/column sampling;
- no tuning or second ranking candidate.

## Legacy result

Paired PR changes:

- F1 `+0.00610555`;
- F2 `+0.00377874`;
- F3 `+0.01915876`;
- F4 **`-0.02533538`**.

Median was positive `+0.00494215`, but q25 `-0.00349979` and worst `-0.02533538` failed the robustness gate. Median Q5-Q1 change was `-0.00721129`, non-below control only `1/4`.

Top-decile overlap with control was low (Jaccard roughly 0.216-0.306), proving the ranker learned a materially different ordering rather than a score rescale.

Verdict: `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`.

## What E proves and does not prove

It provides stronger evidence than V2-D that one genuine group-aware nonlinear ranking objective can improve PR ranking in several periods while destabilizing another period and harming tail separation.

It does **not** prove ranking-native objectives are inferior. It tests one LambdaMART/NDCG configuration only. Its training objective (`rank:ndcg` on binary relevance) is also not identical to the final selection metrics PR-AUC/Q5-Q1, so objective alignment is improved but not complete.

Most importantly, it still optimizes the inherited resolved-only binary TP-vs-SL label. Group-aware learning cannot repair a wrong product estimand or executable-entry mismatch.

V3-E was not clean-replayed; retain it as legacy historical reference only. Do not rerun/tune old LambdaMART on consumed history.

---

# 7. Cross-hypothesis V3 interpretation

## Confirmed historical lessons

Subject to lineage qualifications:

1. Smooth recency weighting did not show a robust advantage in the tested legacy experiment.
2. Structure-Lite contains genuinely new causal technical geometry and retained a strong discovery signal even after PIT-safe correction, but failed clean late confirmation.
3. Hard NORMAL/STRESS expert fragmentation performed poorly under its legacy contract; continuous context remains more defensible than this particular hard routing.
4. Sector-relative remains untested, not failed.
5. LambdaMART learned a genuinely different ranking and improved PR in 3/4 legacy discovery folds, but its F4 failure and weak Q5-Q1 robustness prevented promotion.

## What V3 did not solve

Every scored V3 branch inherited the V1/V2 P0 problems:

- resolved-only future-conditioned target population;
- H10 TP-first/SL-first binary estimand;
- `Close_t` as label-reference rather than proven executable fill;
- fixed ATR barrier geometry;
- no explicit next-session executable entry contract;
- no no-touch/magnitude/payoff state in the primary target;
- no clean demonstration that the model objective equals the product decision objective.

V3 mostly optimized representation/training architecture around the existing target. It did not ask whether the target itself was the right problem.

---

# 8. V3 adversarial criticality ranking

## P0 — generation-level blockers

### P0.1 Inherited target/estimand mismatch

Same as V1/V2; untouched by V3. Any future clean generation should redesign the target family before reusing V3 features.

### P0.2 Executable timing mismatch

Same as V1/V2. Structure breakout at close t may be known after close but the realized trade enters at t+1, not at historical `Close_t` unless a distinct execution contract proves otherwise.

### P0.3 Clean lineage no longer has a V3 champion

The accepted corrected replay explicitly returns `V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`. Treating old V3-B as the clean parent would violate the accepted lineage decision.

## P1 — high-value design/data issues

### P1.1 Structure-Lite late-period instability

Discovery survives correction; F5 does not. Future use of support/resistance geometry should be a separately preregistered block against the clean parent, not inherited by default.

### P1.2 Split/corporate-action price semantics

Longer-horizon level geometry requires a price frame with defensible continuity. Current split diagnostics do not establish that globally.

### P1.3 Regime specialization confounded by discarded warmup and score scales

The old negative V3-C result should close that exact design, not the entire concept of state-conditioned modeling.

### P1.4 Ranking objective remains scientifically open

V2-D modestly beat the linear pointwise comparator; V3-E improved PR in 3/4 folds but failed stability/tail gates. This is mixed evidence, not a closed question. A future test should use the redesigned target, explicit date weighting, and a fair pointwise/group-aware comparison.

### P1.5 Date-centric product versus pooled metrics

V3 still relies heavily on pooled PR/ROC for selection. Same-date Q5-Q1 helps, but future architecture should make per-date weighting and cross-sectional opportunity cost explicit.

## P2 — secondary issues

### P2.1 Structure semantic arbitrariness

Fixed pivot, cluster, touch, retest and volume constants are defensible preregistered priors but not proven invariant mechanisms.

### P2.2 Structure feature denominator ambiguity

Role-reversal count lacks cluster/opportunity denominator; touch counts similarly mix persistence and opportunity frequency.

### P2.3 Sector-relative remains data-blocked

Potentially useful but should not hold up core model redesign.

---

# 9. What should survive from V3

Retain as research principles:

- hypothesis-by-hypothesis preregistration;
- exact incumbent control equivalence;
- paired promotion gates and late-development confirmation;
- fail-closed PIT sector handling;
- causal left-only support/resistance construction rather than centered pivots;
- explicit no-rescue behavior after a failed gate;
- keeping group-aware ranking as an open architecture axis rather than assuming binary classification is optimal.

Do not automatically inherit:

- old V3-B as clean parent;
- any V3-A/C/E fitted artifact as clean evidence;
- exact Structure-Lite constants;
- hard NORMAL/STRESS routing;
- LambdaMART parameters/objective;
- the resolved-only H10 target or Close_t execution geometry.

---

# 10. Final V3 verdict

`V3_FORENSIC_CLOSED_CLEAN_PARENT_REMAINS_V2`

V3 was a disciplined and scientifically useful hypothesis ladder, but it does not currently supply a surviving clean architecture beyond Clean V2.

The strongest V3 lesson is V3-B: causal support/resistance geometry produced meaningful discovery-fold incremental signal, yet the clean PIT-safe late confirmation failed. This makes Structure-Lite an interesting future information block, not a retained parent.

V3-C and V3-E add useful negative/mixed architecture evidence but remain legacy contaminated-reference results because they were not part of the accepted corrected replay. V3-D remains untested and data-blocked.

The next generation should not be a V3 rescue. Before any new clean ranker, priority remains:

1. redesign target/estimand contract;
2. freeze executable t+1 timing semantics;
3. define date/group weighting and learning objective deliberately;
4. retain Clean V2 as incumbent benchmark;
5. only then reconsider independently admissible representation blocks such as Structure-Lite, Foreign Flow state, price/trend state, free-float/supply interactions, fundamentals, or event state.

## Stop boundary

Do not launch a V3 rescue or replay V3-A/C/E from this audit. Do not inspect protected fresh-forward outcomes. The next intended forensic generation, when requested, is O2.
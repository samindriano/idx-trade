# Ranking V3 Roadmap Audit V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **ROADMAP / RESEARCH-GOVERNANCE FREEZE — NOT AUTHORIZATION TO RUN V3 OUTCOMES**

## Purpose

Re-audit the Ranking-V3 research roadmap after reviewing the frozen Ranking-V2 result and the private legacy Indonesian-stock model archive. This document defines how V3 research should proceed without recreating the earlier feature/model/threshold soup, without contaminating the reserved V2 fresh-forward block, and without treating repeated historical development runs as independent validation.

Read together with:

- `docs/CURRENT_STATUS.md`;
- `docs/RANKING_V3_RESEARCH_BACKLOG.md`;
- `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`;
- `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
- the newest controlling checkpoint/specification.

Nothing here changes Ranking V2, starts Stage 6, starts probability calibration, authorizes execution-PnL, or authorizes fresh-forward outcome access.

## Executive audit conclusion

The V3 hypothesis ladder is revised to:

1. **V3-A — RECENCY**
2. **V3-B — STRUCTURE-LITE**
3. **V3-C — REGIME-SPECIALIZATION**
4. **V3-D — SECTOR-RELATIVE**
5. **V3-E — TRUE-RANKING**

The main change is moving `STRUCTURE-LITE` ahead of explicit regime gating.

Reasoning:

- V2 already showed that explicit market context helps and the frozen HGB model can already learn nonlinear interactions between stock and market-state features;
- a hard/explicit regime-expert architecture immediately adds sample fragmentation and more model degrees of freedom;
- legacy support/resistance work contains useful causal geometry ideas that are not yet represented well by V2's simple recent-high/recent-low distances;
- a small structure family can therefore add genuinely new information while retaining the exact V2 model, target, and market-context representation;
- old downside-ranking and current pairwise-linear results both warn that changing the objective alone should remain lower priority.

This ordering is a research priority, not a claim that any lane will work.

## V2/V3 isolation rule

Ranking V2 remains a frozen forward-validation track. V3 may proceed asynchronously only on development knowledge already available through `2026-07-31`.

Until a separately reviewed forward protocol says otherwise:

- do not read reserved post-2026-07-31 V2 forward outcomes for V3 development;
- do not use V2 forward PASS/MIXED/FAIL to choose a V3 candidate;
- do not write or trigger `FORWARD_OUTCOME_ACCESS_STARTED` from V3 work;
- do not alter the V2 champion, 25-feature contract, final model, or V2 one-shot verdict rules.

If V2 forward outcomes are learned before the final V3 architecture is frozen, those outcomes become development knowledge for V3 and cannot serve as V3's independent validation block.

## Historical-development truth

All V3 historical experiments on data through `2026-07-31` are **development evidence only**.

The V2 chronological folds may be reused for comparability, purge discipline, and robustness diagnostics, but repeated V3 experiments on those folds are not new independent tests. The project must track the cumulative number of hypotheses/candidates evaluated so apparent robustness is not mistaken for untouched evidence.

No unused part of the pre-2026-07-31 history should later be called an independent test merely because V3 did not fit on that exact row. The entire period is already project development knowledge.

## Global V3 research discipline

### One hypothesis per experiment

Every V3 experiment must answer one falsifiable question. Do not simultaneously change feature family, model family, target, weighting, regime policy, and selection rule.

### Exact V2 control in every experiment

The comparator is the frozen V2 `HGB_XS_MARKET` semantics on the same eligible rows/folds. A V3 variant must beat the real V2 champion, not a weaker reconstructed baseline.

### Small candidate budget

Each primary experiment should normally contain:

- one exact V2 control; and
- at most two bounded variants of the single hypothesis under test.

Any exception requires a written justification before outcome access. A model zoo, broad threshold grid, broad feature toggle search, ensemble enumeration, or many-decay sweep is prohibited.

### Hypothesis ledger

Every evaluated variant must be recorded permanently with:

- hypothesis ID and parent;
- specification SHA/commit;
- exact data/cache/fold identity;
- exact feature/model/parameter identity;
- whether the result was viewed;
- primary and robustness metrics;
- verdict `PROMOTE_FOR_NEXT_RESEARCH_STEP`, `KEEP_DIAGNOSTIC`, or `KILL`;
- cumulative candidate count already tried in the V3 generation.

Failed variants are not silently deleted from the research denominator.

### Robustness-first evidence

Do not optimize on mean/median headline metric alone. At minimum report:

- median PR-AUC delta versus prevalence;
- 25th-percentile PR-AUC delta;
- worst-fold PR-AUC delta;
- positive-delta fold count;
- median ROC-AUC and ROC>0.5 fold count;
- median and worst-fold Q5-Q1 TP-rate spread;
- top-decile lift;
- late-fold behavior;
- selected/incremental-name diagnostics where a change expands or materially alters the top-ranked set.

### No post-result rescue

After an experiment result is viewed, its candidate definitions, thresholds, feature bundle, model family, and pass/kill rule are closed. A materially new follow-up requires a new hypothesis ID/spec and is counted as another development experiment.

## Two-tier V3 development protocol

To reduce repeated adaptation to the same late historical periods, V3 should use a two-tier development process.

### Tier 1 — hypothesis discovery

Use the earlier frozen chronological development folds/blocks only for bounded hypothesis screening. The exact discovery folds must be frozen in each first V3 spec before any V3 outcome run.

Recommended default: use the first four V2-style chronological folds for discovery because they provide multiple regimes while reserving the latest two folds from repeated V3 candidate iteration.

Every Tier-1 experiment remains development evidence.

### Tier 2 — late-development confirmation

After the individual hypothesis ladder and any single predeclared integration step are complete, freeze one final V3 architecture **before** inspecting its results on the reserved latest development folds.

Recommended default: use V2-style folds 5 and 6 once as a late-development confirmation for the final V3 architecture.

Important: these folds are **not independent validation** because their period and V2 behavior are already known to the project. Their purpose is only to reduce V3-specific adaptive reuse and test transportability to the latest historical development regimes.

Do not repeatedly reopen folds 5/6 for every V3 idea. If they are consumed early for a V3 candidate, record that consumption and do not later describe them as a one-shot V3 confirmation.

## V3-A — RECENCY

### Question

Does reducing the influence of older development observations improve ranking robustness under temporal drift?

### What stays fixed

- H10 first-touch target and label semantics;
- universe and causal data contract;
- exact 25 V2 features;
- `HGB_XS_MARKET` estimator architecture/hyperparameters;
- chronological purge/maturity rules;
- score and ranking metrics.

### What may change

Only fit-row sample weights as a deterministic function of age within each training fold.

The executable specification must freeze:

- exact age definition in official sessions;
- at most two half-lives/weight schedules plus uniform control;
- whether weights are normalized and why;
- deterministic handling at fold boundaries;
- eligibility and kill rule.

Do not search many half-lives after seeing outcomes. The backlog examples near one and two trading years are candidate ideas only until the spec freezes them.

### Promotion logic

Promote recency only if it improves downside robustness of the metric distribution (q25/worst/late-fold and stability) without materially degrading the central ranking metrics. A tiny median gain accompanied by worse worst-fold behavior is not enough.

If neither bounded recency candidate improves robustness, close the recency hypothesis and keep uniform weighting.

## V3-B — STRUCTURE-LITE

### Question

Does a compact causal price-geometry representation add information beyond V2's recent-high/recent-low distances and range position?

### Design principle

Retain the exact V2 target/model/market-context semantics. Add only one small preregistered structure bundle. Do not import the legacy support/resistance decision layer.

Candidate feature concepts for the future spec may include a bounded subset of:

- support/resistance touch density using only prior data;
- level age/recency;
- role-reversal evidence;
- breakout/retest state;
- volume confirmation;
- range/volatility compression.

Because V2 already includes 20/60 high-low distances and 20-session range position, the V3 bundle should avoid simply duplicating those existing features.

### Hard prohibitions

Do not use:

- outcome-conditioned setup buckets;
- historical test/backtest return lookups;
- ticker-specific empirical overlays;
- adaptive horizon weights;
- hand-tuned investment-score bonuses;
- a large technical-indicator library.

### Promotion logic

Promote only if the fixed bundle improves robust ranking separation against V2. If the bundle passes, any later feature-level ablation is a **separate** research experiment; do not retroactively prune features using the same viewed confirmation outcomes.

## V3-C — REGIME-SPECIALIZATION

### Question

After market context is already present in V2, does explicit conditional specialization add value beyond the nonlinear HGB's existing interactions?

### Why third

This is intentionally after recency and structure because regime gating adds model complexity and fragments training samples.

The future spec must use a small causal regime definition derived from information available at close T. Prefer two or at most three broad states. Freeze the state definition before outcome access and forbid a grid search over regime thresholds.

Possible forms include a bounded expert/gating design or another explicitly conditional architecture, but only one formulation should be tested at a time.

### Promotion logic

The primary requirement is improvement in worst-regime/worst-fold behavior without sacrificing broad coverage and overall ranking separation. A specialist that excels only in one regime and weakens the rest is not a promotion.

## V3-D — SECTOR-RELATIVE

### Question

Does same-date stock strength relative to its own sector add incremental information beyond whole-market relative features?

### Prerequisite data gate

No model experiment is authorized until point-in-time sector membership is proven with:

- source provenance;
- effective dates;
- historical changes/reclassifications;
- ticker/security identity mapping;
- no use of current-sector backfill into history;
- coverage and missingness diagnostics;
- immutable snapshot/hash contract.

Sector-map engineering may proceed asynchronously as infrastructure while earlier V3 hypotheses are researched, but its model outcomes remain blocked until the PIT gate passes.

### Possible later feature family

Keep it compact: within-sector rank, stock-minus-sector median, and sector-vs-market state for a small subset of the already-frozen V2 raw concepts. Do not recreate a large sector-specific model zoo.

## V3-E — TRUE-RANKING

### Question

Does a nonlinear same-date ranking objective outperform the frozen binary HGB ranking score?

### Why fifth

- current V2 pairwise logistic did not win;
- an older preregistered downside-ranking experiment also failed its champion comparison;
- changing the objective is therefore not sufficient evidence by itself.

A future experiment should test one tightly bounded tree/LambdaMART-style ranking formulation with signal date as the query group and predeclared parameters. Do not run a library/model tournament.

## Integration rule: do not rebuild the legacy monster

Individual hypothesis winners do **not** automatically get stacked together.

After Tier-1 experiments, permit at most one preregistered integration experiment whose components are limited to independently surviving hypotheses. The integration spec must be frozen before running it and must compare:

- exact V2 control;
- best single surviving V3 component;
- one combined candidate.

If the combined candidate does not improve robustness materially over the best single component, keep the simpler model.

Do not test every combination of surviving features/architectures. Complexity itself is a cost and the deterministic tie preference should favor the simpler surviving architecture when performance is practically tied.

## Separate research lanes, not first-pass V3 ranking features

### Distribution / uncertainty

U1-style q10/q50/q90 forecasting remains a later uncertainty layer. It may estimate tail geometry and uncertainty width, but ranking score must not be relabeled as calibrated probability.

### Path risk

V4-style MAE/MFE/path modeling remains a separate risk/veto/geometry layer. A path-risk win does not imply a better opportunity ranker.

### Broker flow / EventRank / fundamentals / macro expansion

These require separate point-in-time data and availability gates. `captured_at` is not automatically `available_at`; missing observations are not zero; revisions must be explicit. Do not add alternative-data features merely because ingestion code exists.

## Runtime and compute rules

Before every V3 implementation, the agent must explicitly confirm reading `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`.

Use:

`one operator/Codex -> deterministic Python orchestrator -> bounded compute workers`

Profile the post-cache workload before adding concurrency. Engineering optimization must prove semantic equivalence before it is used for any outcome-bearing run.

Do not use many Codex chats as an uncontrolled candidate scheduler and do not run unrelated V3 compute while a sensitive V2 outcome-access operation is occurring.

## What should happen next

The next executable V3 task is **specification only**, not scoring:

`RANKING_V3_RECENCY_SPEC_V1`

It must freeze:

- exact discovery-fold contract;
- exact V2 control;
- at most two recency variants;
- weight formula/half-lives/normalization;
- exact candidate count;
- metrics and robustness gates;
- promotion/kill rule;
- hypothesis-ledger schema;
- provenance/runtime contract;
- explicit reserved-V2-forward prohibition;
- explicit stop after producing the frozen spec/checkpoint/handoff.

Only after independent review of that spec should Codex be authorized to implement and run the first V3 scores.

## Current authorization boundary

This roadmap audit authorizes documentation and future specification preparation only. It does **not** authorize:

- V3 model fitting/scoring/outcome evaluation;
- any fresh-forward outcome access;
- V2 changes;
- Stage 6;
- probability calibration;
- execution-PnL;
- paper/live trading;
- merge to `main`.

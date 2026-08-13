# Ranking V3 — Legacy Indonesian-Stock Model Lessons

Date: 2026-08-10 (Asia/Jakarta)
Status: **RESEARCH LESSONS / IDEA EVIDENCE ONLY — NOT AUTHORIZATION TO RUN V3**

## Purpose

Record reusable lessons from the private archive `samindriano/past-models-indo-stock` so Ranking V3 does not repeat earlier model-selection and feature-engineering failure modes.

The archive is a learning source only. Historical model scores, thresholds, test results, and live-looking outputs in the archive are **not promotion evidence** for `idx-trade`. Every useful idea must be reformulated as a new causal, point-in-time-safe, preregistered hypothesis against the current frozen V2 champion.

Reserved V2 fresh-forward outcomes remain off-limits. Nothing in this note authorizes reading them or using them to choose V3 architecture.

## Archive provenance reviewed

Primary archive catalog:

- repository: `samindriano/past-models-indo-stock`;
- catalog: `ARCHIVE_CATALOG.md`;
- catalog records both Git-derived snapshots and `LOCAL-UNTRACKED` standalone local projects.

High-value sources reviewed:

1. `model/big3-bank-quant` — archive head `0f2ebdeb9ee691835a90067b75c004087656d91f`;
2. `frontend/indo-stock-lookup-support-resistance` — archive head `b10f1f619d99590028823addb2cd497333aff20f`;
3. `model/v2-daily` — archive head `3e9d3aaf89a437047fb8356e546a843badd60b85`;
4. `model/trading-v2-ranked-swing` — archive head `a3edf5c07018e41d109f018da8817e7aa2ad227f`;
5. `model/v4-path-risk` — archive head `5fdb184746c9866c804cad901e035e279d2d524e`;
6. `model/u1-two-sided-quantile-swing` — archive head `640cc130739ab38ba5e7ee73241f4bdfac4b0b52`;
7. `model/u2-broker-flow-ranking` — archive head `33dddff6cca2248424abf838a288e745d7ffae4c`;
8. `research/eventrank-v0-mainline` — archive head `4b2fee0b2d2415173d919ac64f00725a629baa30`.

The BBCA strategic-baseline notebook and legacy frontend branches were reviewed as lower-priority context; they are not direct model evidence for Ranking V3.

## Main autopsy: Big3 Bank Quant

This is the closest match to the earlier high-complexity / overfit-prone project.

The project simultaneously exposed many research degrees of freedom:

- horizons `7/20/50/100/200` plus separate return forecasts;
- model families Logistic Regression, Random Forest, Extra Trees, XGBoost, LightGBM, and HistGradientBoosting;
- model-recipe combinations / ensembles;
- threshold search roughly `0.35..0.65` in `0.01` increments;
- technical, market-context, macro-regime, valuation, dividend, event, short-term, intraday, and bank-character feature families;
- optional horizon-specific feature activation;
- recent-training-window controls;
- ticker dummy variables;
- separate recent-block and walk-forward selection logic.

Many individual ideas are reasonable. The research problem was that too many were activated or selectable inside one architecture/search process, so a good-looking result could not reliably identify which causal hypothesis created the edge.

A particularly important pattern is repeated adaptation to validation evidence: candidate model selection, recipe/ensemble enumeration, and threshold optimization all create a large effective search space. This can overfit validation even when the final nominal test partition is not directly used for fitting.

### What to salvage

Treat these only as isolated future hypotheses:

- recency / non-stationarity;
- explicit market regime/context;
- stock-relative-to-market or peer context;
- richer causal price structure;
- event context only with provable announcement-time availability;
- macro context only as a separately justified hypothesis;
- uncertainty/range modeling as a separate decision/risk layer.

### What not to port

Do not port the Big3 model zoo, adaptive recipe search, broad threshold search, ticker-specific recipe behavior, or all feature families at once.

Do not treat old apparent accuracy as evidence that any one feature family works. The old design has insufficient attribution for that conclusion.

## Support/resistance: geometry is useful, decision layer is not

The standalone support/resistance application contains a useful causal geometry engine:

- rolling/window extrema;
- local pivot candidates;
- clustered nearby levels;
- touch counts;
- level recency;
- role reversals;
- distance from current price;
- primary/secondary support and resistance selection;
- breakout / failed-breakout state;
- chart anchors for historical touches.

This is valuable inspiration for a future `V3-STRUCTURE` or later structure-feature experiment.

However, its downstream decision layer is not safe to port as model evidence. It uses historical routed test predictions and range-backtest outcomes to condition current setup scores, empirical probabilities, ticker/setup-specific weights, and horizon weights. Some conditional groups allow very small sample counts. That is an archetypal post-hoc adaptation path and can manufacture convincing-looking current scores from reused historical outcomes.

### Safe V3 structure rule

If structure is tested later, expose only frozen causal numeric features such as:

- distance to prior support/resistance in ATR units;
- number of prior touches;
- cluster density;
- level age / recency;
- role-reversal count;
- breakout/retest indicator;
- volume confirmation;
- compression/range-location measures.

Freeze definitions before scoring. Do not use outcome-conditioned setup buckets, ticker-specific empirical backtest overlays, or hand-tuned investment-score bonuses as model inputs or promotion criteria.

## Old V2 lesson: coverage expansion can dilute edge

The clean historical `model/v2-daily` comparison is useful negative evidence.

On exact matched rows, the old V2 bearish specialist increased call coverage materially but reduced precision and avoided-loss quality versus V1.1. The additional V2-only calls were close to noise economically, while bullish produced no valid calls.

General lesson for current V3:

- never reward coverage expansion by itself;
- report incremental-only quality separately from combined quality;
- require any extra selected names to preserve meaningful ranking separation;
- a larger opportunity set is not automatically a better signal engine.

## Old downside-ranking lesson: ranking objective is not automatically superior

The old preregistered downside-ranking V3 changed the problem from classification to same-date ranking. It still failed its frozen gates: same-call results were weaker than the old champion and expansion calls were poor.

This does **not** prove that current nonlinear learning-to-rank is useless. It does prove that “ranking is more natural” is not sufficient evidence by itself.

Therefore current `V3-TRUE-RANKING` should remain a bounded hypothesis with the frozen V2 champion as control, not a broad ranking-library tournament or assumed upgrade.

## Old V4 lesson: path risk and opportunity are different targets

The old V4 path-risk experiment predicted the worst five-session path excursion. It could select slightly more adverse MAE while still degrading endpoint excess-return / endpoint bearish quality and failing stability gates.

General lesson:

- a path-risk model can be useful even when it is not a better opportunity ranker;
- MAE/MFE, drawdown-before-target, and touch risk should remain separable from opportunity ranking;
- if a future path-risk model is revived, use it as a risk/geometry overlay or veto layer, not as silent replacement for the H10 opportunity target.

## U1 lesson: distributional forecasts are conceptually strong but unproven

The old U1 design proposed whole-universe q10/q50/q90 forecasts of T+5 excess return with explicit uncertainty width, tail asymmetry, per-date transforms, causal support/resistance features, strict HOLD defaults, and no broad model search.

It was blocked by universe/provenance constraints and therefore provides **zero empirical evidence of edge**.

Still, the conceptual separation is useful for a later phase:

- ranking model decides relative opportunity;
- distribution/quantile model estimates uncertainty and tail geometry;
- risk/action layer consumes both without pretending ranking score is a calibrated probability.

Do not add this complexity to the first V3 recency experiment.

## U2 / EventRank lesson: alternative data begins as a data problem

Broker flow and event-study ideas were correctly blocked behind point-in-time availability, revision, licensing/coverage, and source-readiness contracts.

Important rules to retain:

- `captured_at` is not automatically `available_at`;
- missing broker/ticker/session observations are unknown, not zero;
- corrections must be append-only/versioned;
- no alternative-data feature gets model credit merely because ingestion code exists;
- event/fundamental dates require provable information-availability time, not only event date.

For current V3, broker flow / EventRank should remain infrastructure backlog until the data can pass a new PIT gate.

## Revised interpretation of the current V3 ladder

The legacy archive strengthens, but does not validate, the current hypothesis ordering.

### Keep Priority 1 — V3-RECENCY

The old Big3 project already contained recent-window controls, confirming this is not a new intuition. But because it was mixed with many other knobs, it supplies no clean evidence that recency worked.

Current V3 should test recency in isolation with the same V2 features/model/label and only a very small predeclared candidate set.

### Keep Priority 2 — V3-REGIME, but constrain it harder

The legacy project used IHSG, USD/IDR, VIX, rates, peer strength, macro and event context. Current V2 already gives cleaner evidence that explicit market context matters.

A V3 regime experiment should therefore use a small causal state definition and test conditional specialization only. Do not recreate the broad macro-feature soup.

### Promote a future V3-STRUCTURE-LITE hypothesis into the backlog

The support/resistance archive and U1 design both contain useful geometry ideas. After recency, a tightly bounded structure experiment may be more interpretable than a large model-family change.

Suggested feature family for specification work only:

- prior high/low 20/60 ATR distance;
- causal pivot/touch density;
- level recency/age;
- role reversal;
- breakout/retest;
- volume confirmation;
- compression/range position.

No outcome-conditioned empirical setup weights.

### Keep V3-SECTOR-RELATIVE conditional on PIT mapping

The old Big3 “peer” features used a tiny bank universe and are not evidence for sector-wide benefit. Current V3 still requires a genuine historical PIT sector map before within-sector ranks are allowed.

### Keep V3-TRUE-RANKING lower priority

Both the old downside-ranking experiment and current V2 pairwise-linear candidate show that changing the objective alone is not guaranteed to improve transportability. A future nonlinear ranker must beat the exact V2 champion under the same robustness-first protocol.

### Defer distributional and path-risk models to separate lanes

U1-style quantiles and V4-style path risk are potentially useful, but they answer different questions from primary opportunity ranking. They should be researched as explicit secondary layers after the primary ranker has stronger evidence.

## Overfitting guardrails derived from the archive

For every V3 experiment:

1. One experiment should answer one falsifiable question.
2. Freeze feature family, model family, parameters, candidate count, metric, eligibility, and tie-break before outcomes are inspected.
3. Keep the effective search space small; model families × feature toggles × thresholds × ensembles × horizons multiply into hidden researcher degrees of freedom.
4. Never adapt current scoring using historical test/backtest buckets that were selected after seeing their realized outcomes.
5. Report q25/worst-fold/latest-fold and incremental-only quality, not only averages or best periods.
6. A failed hypothesis is closed unless a genuinely new preregistered question justifies a new version.
7. Reserved V2 fresh-forward outcomes remain unavailable to V3 R&D.

## Immediate implication

No change to the current V2 forward contract.

For V3, the preferred first executable research specification remains a narrow recency experiment. This archive review adds a strong requirement that the specification explicitly limits effective search degrees of freedom and records `V3-STRUCTURE-LITE` as a later independent hypothesis rather than merging legacy technical, macro, event, support/resistance, sector, and ensemble ideas into one model.

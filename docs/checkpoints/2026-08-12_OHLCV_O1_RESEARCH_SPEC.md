# OHLCV O1 — Frozen Research Specification

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o1-v1`
Base review commit: `1d6709ecac589c7578b20b029041e125189d1ebc`
Decision: `OHLCV_O1_HISTORICAL_DEVELOPMENT_AUTHORIZED`

## Research question

Does adding current-session Open information through a minimal overnight/intraday decomposition improve the frozen V3-B Structure-Lite ranker on the exact same historical-development rows?

This is a challenger experiment. Canonical `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` remains frozen and is not overwritten or retuned.

## Mandatory data population

Use exactly the 278,168-row all-five-Open-feature-ready common-support intersection certified by the Open research coverage gate.

The row identity set must be loaded from the preserved coverage-gate artifact and hash-pinned before training. Both baseline and all challengers must use exactly the same row identities.

Do not enlarge the common-support set merely because O1A/O1B technically need fewer fields. The first experiment intentionally uses one common population for all candidates to keep attribution clean.

## Baseline and challengers

### `V3B_COMMON_SUPPORT_BASELINE`

Exact canonical V3-B Structure-Lite feature order, transformation semantics, HGB pipeline, parameters, H10 labels, six development folds, and evaluation semantics; only the row population changes to the frozen 278,168-row common-support set.

### `O1A_OVERNIGHT`

Baseline plus one feature:

`overnight_gap = Open_t / prior_close - 1`

`prior_close` must be the previous observed ACTIVE bar for the same ticker under the causal panel chronology already certified by the coverage gate.

### `O1B_INTRADAY`

Baseline plus one feature:

`intraday_return = Close_t / Open_t - 1`

### `O1C_DECOMPOSITION`

Baseline plus both O1A and O1B features, in a deterministic frozen order.

No other Open-derived feature is allowed in this run.

## Exact-contract preflight

Before any model fit, verify and record:

- canonical V3-B candidate identity;
- canonical final feature order and feature-order hash;
- exact HGB estimator/pipeline and parameters;
- exact H10 target/label contract;
- exact six historical-development fold identities and gap/purge semantics;
- V3-B final-refit table/manifest hashes;
- common-support row-identity artifact/hash;
- immutable panel and accepted Open derivative hashes.

If any exact V3-B contract cannot be reproduced from frozen evidence, stop with a factual blocker. Do not approximate.

## Training protocol

- Historical-development data only, through 2026-07-31.
- Same six chronological folds for all four models.
- Same train/validation row identities within each fold after common-support filtering.
- Same preprocessing and estimator parameters across baseline/challengers except deterministic appended feature columns.
- No hyperparameter tuning.
- No early candidate-specific adaptation after metrics are observed.
- Reuse existing efficient label/evaluation paths where semantics are proven equivalent.

## Metrics

Report per fold and aggregate:

- prevalence;
- PR-AUC;
- PR-AUC minus prevalence;
- paired challenger PR-AUC minus common-support-baseline PR-AUC;
- ROC-AUC;
- Q5-Q1 under the frozen V3/V2 ranking semantics;
- top-decile lift if supported by the canonical evaluator;
- train/validation row counts;
- feature order/hash;
- training runtime.

Also report candidate comparison by historical era/year or another deterministic diagnostic sufficient to reveal whether apparent uplift is concentrated in early low-Open-coverage history.

## Survivor rule

This run is not a champion-replacement decision. It only decides whether an Open-decomposition family deserves a next experiment.

A challenger may be labeled `O1_SURVIVOR` only if:

1. median paired PR-AUC improvement over `V3B_COMMON_SUPPORT_BASELINE` is > 0;
2. lower-quartile paired PR-AUC improvement is > 0;
3. improvement is not explained by one isolated fold spike;
4. aggregate ranking guardrails do not show a clear reversal versus the common-support baseline.

If no challenger satisfies these conditions, decision is `O1_NO_SURVIVOR` and Open decomposition is not expanded automatically.

If one or more survive, stop for independent review before any O2/Open-geometry/interaction experiment.

## Protected boundary

Do not access any post-2026-07-31 fresh-forward outcome, reserved V3-B/V2 forward outcome block, or global outcome-access marker.

Historical development outcomes already used by V3-B may be used only under the frozen development folds for this preregistered challenger experiment.

## Prohibited scope

- no canonical V3-B overwrite or challenger final refit;
- no forward validation;
- no additional Open features;
- no HGB parameter search;
- no sector/PIT experiment;
- no Path Risk/probability/payoff/reliability work;
- no execution-grade promotion;
- no execution PnL, paper/live, or broker work;
- no network/provider calls;
- no remaining-Open repair.

## Required output

Persist a dated factual runtime checkpoint and immutable external artifacts with hashes, including exact row identities, feature manifests, fold metrics, aggregate paired comparison, and survivor/no-survivor decision. Run focused tests and full pytest, push fast-forward, then stop for independent ChatGPT review.

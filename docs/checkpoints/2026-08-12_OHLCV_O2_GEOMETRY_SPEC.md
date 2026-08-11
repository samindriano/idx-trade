# OHLCV O2 Geometry — Frozen Research Specification

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-geometry-v1`
Parent independent-review commit: `a8ad3acc904bdd6f966319a75b52efcd951addd9`
Decision: `OHLCV_O2_GEOMETRY_HISTORICAL_DEVELOPMENT_AUTHORIZED`

## Research question

Does current-session Open location within the completed daily H/L range provide robust incremental H10 ranking information beyond canonical V3-B Structure-Lite?

O1 overnight/intraday decomposition is closed as `O1_NO_SURVIVOR`. This experiment must not attempt to rescue O1.

## Population and baseline

Use exactly the same 278,168-row common-support identity set used by O1, hash-pinned from the preserved coverage-gate/O1 artifacts.

Reproduce exactly:

`V3B_COMMON_SUPPORT_BASELINE`

with canonical 33-feature order/hash, frozen HGB preprocessing/parameters, H10 labels, six folds and evaluation semantics.

Do not recompute or enlarge the population from the panel.

## Single challenger

Train exactly one challenger:

`O2_OPEN_GEOMETRY`

Feature order is canonical V3-B 33 features followed by exactly:

1. `open_position = (Open_t - Low_t) / (High_t - Low_t)`;
2. `open_to_high = High_t / Open_t - 1`;
3. `open_to_low = Low_t / Open_t - 1`.

Use the already-certified causal feature values from the Open coverage-gate artifact where possible. `open_position` remains undefined for flat H/L bars; the frozen 278,168 common-support set already excludes rows where all required Open features are not ready.

No other Open-derived feature is allowed.

## Training and evaluation

- history through 2026-07-31 only;
- identical train/validation rows for baseline and challenger in each fold;
- exact six O1/V3-B development folds;
- exact frozen HGB pipeline and parameters;
- no hyperparameter tuning;
- no candidate-specific preprocessing change;
- no feature interaction or nonlinear hand-engineered derivative beyond the three frozen features;
- no regime split/model, year-specific adaptation or threshold optimization;
- no use of O1 metrics to alter this specification.

Report per fold and aggregate:

- prevalence;
- PR-AUC and PR-AUC minus prevalence;
- paired challenger-minus-baseline PR-AUC delta;
- ROC-AUC;
- Q5-Q1;
- top-decile lift;
- row counts;
- feature order/hash;
- runtime;
- deterministic historical-era diagnostic without changing the decision rule.

## Survivor rule

`O2_OPEN_GEOMETRY` survives only if all are true:

1. median paired PR-AUC delta > 0;
2. lower-quartile paired PR-AUC delta > 0;
3. uplift is not explained by one isolated fold spike;
4. no clear aggregate ranking guardrail reversal versus the common-support baseline.

Otherwise decision is `O2_NO_SURVIVOR`.

## Hard-stop consequence

If decision is `O2_NO_SURVIVOR`, close the Open-derived alpha-feature lane under the current V3-B/HGB/H10 architecture. Do not start O3, gap/ATR variants, Open interactions, regime-conditioned Open features or feature mining.

If O2 survives, stop for independent ChatGPT review before any combination/final-refit decision.

## Protected boundary

Do not access any post-2026-07-31 fresh-forward outcome or write any forward-outcome access marker.

Do not overwrite canonical V3-B, perform a challenger final refit, repair remaining Open, promote execution grade, start Path Risk/probability/payoff/reliability, execution PnL, paper/live or broker work.

## Required output

Persist a factual dated runtime checkpoint and immutable external artifacts/hashes for preflight contract, row identities, feature manifest, fold metrics/predictions, aggregate comparison, era diagnostic and survivor decision. Run focused and full pytest, push fast-forward, then STOP for independent ChatGPT review.

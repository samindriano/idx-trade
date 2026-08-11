# OHLCV O1 — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Reviewed runtime HEAD: `fa9baf87df42b269b87e2919293a724b93374cfe`
Decision: `O1_NO_SURVIVOR_ACCEPTED_O2_GEOMETRY_SINGLE_TEST_AUTHORIZED`

## Review verdict

The runtime decision `O1_NO_SURVIVOR` is accepted.

The experiment respected the frozen contract:

- exact 278,168-row common-support population;
- exact canonical 33-feature V3-B order/hash;
- identical six historical-development folds, labels, evaluator and HGB parameters for baseline and challengers;
- no hyperparameter tuning;
- no post-2026-07-31 fresh-forward outcome access;
- canonical V3-B remained frozen.

All three O1 challengers fail the preregistered lower-quartile paired PR-AUC improvement gate:

- O1A median `+0.000172`, q25 `-0.001568`, positive folds `3/6`;
- O1B median `+0.001816`, q25 `-0.000354`, positive folds `4/6`, aggregate guardrail reversal `true`;
- O1C median `+0.002154`, q25 `-0.000526`, positive folds `4/6`.

The large V2F6 gain for O1C (`+0.025485`) cannot rescue the family because V2F4 is materially negative (`-0.012118`) and the frozen robustness rule explicitly requires a positive lower quartile. No post-hoc fold selection or tuning is authorized.

## Interpretation

This result rejects the narrow hypothesis that raw overnight gap and/or raw same-day intraday return provide robust incremental alpha over V3-B under the frozen HGB/H10 historical-development contract.

It does **not** prove that all information contained in Open is useless. Canonical V3-B already contains close-position, high/low-distance and support/resistance structure features, but it contains no direct Open-location-within-current-day-range feature. That is a conceptually distinct, bounded hypothesis.

## Final bounded Open-alpha authorization

Authorize exactly one orthogonal follow-up family: `O2_OPEN_GEOMETRY`.

The follow-up must:

- use the same exact 278,168 common-support row identities;
- reproduce the same `V3B_COMMON_SUPPORT_BASELINE` contract;
- train exactly one challenger with these three already-certified causal features:
  - `open_position = (Open_t - Low_t) / (High_t - Low_t)`;
  - `open_to_high = High_t / Open_t - 1`;
  - `open_to_low = Low_t / Open_t - 1`;
- append the three features in the frozen order above;
- use the same six folds, target, HGB pipeline/parameters and evaluator;
- perform no feature interaction, normalization variant, threshold search, hyperparameter search, regime-specific adaptation or O1-informed rescue;
- apply the same robustness logic: median paired PR-AUC delta > 0, lower-quartile paired delta > 0, uplift not driven by one fold, and no clear aggregate ranking guardrail reversal.

This is deliberately a **single candidate**, not another model zoo.

### Hard stop

If `O2_OPEN_GEOMETRY` does not survive the frozen gate, the Open-derived alpha-feature lane is closed under the current V3-B/HGB/H10 architecture. Do not proceed to O3, interactions, gap/ATR engineering or feature mining to rescue Open.

Open data may still be used later for separately specified Path Risk, execution/cost, intraday research, or a genuinely new architecture, but failure of O2 must not be mined further inside this alpha lane.

## Protected boundary

No fresh-forward outcome access is authorized. No canonical V3-B overwrite/final refit, execution-grade promotion, remaining-Open repair, Path Risk, probability/payoff/reliability, execution PnL, paper/live or broker work is authorized by this checkpoint.

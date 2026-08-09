# IDX Trade V1 Research Specification

Status: FROZEN STAGE-2 SPECIFICATION CANDIDATE
Date: 2026-08-09 (Asia/Jakarta)
Project mode: EXPLORATORY_RESEARCH_ONLY

This document freezes the first signal-research question and its validation
contract. It does not authorize feature or label implementation, model
training, tuning, prediction, paper trading, or live trading. A separate Stage
3 approval is required before any of those activities begin.

## 1. Immutable input and scope

The input is the certified `SIGNAL_RESEARCH_HLCV` panel documented in
`docs/SIGNAL_RESEARCH_HLCV_CONTRACT.md`:

- exact window: `2021-04-29 -> 2026-07-31`;
- 1,260 official IDX exchange sessions;
- 981,940 ACTIVE rows;
- panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- separate research manifest SHA-256:
  `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`;
- manifest verification: `valid=true`, 15/15 artifacts.

The research panel is immutable input. It must not be rewritten, adjusted,
redownloaded, or supplemented with synthesized Open values in this Stage 2
contract. `SIGNAL_RESEARCH_HLCV` is not an execution-grade price contract.

The research unit is `security x signal_date`. The primary universe is IDX
listed common shares in point-in-time scope. `CNTX` remains excluded as an
authoritative non-common share. `UNKNOWN` rows are not relabelled and are
excluded from signal features, labels, liquidity metrics, and execution paths.

## 2. Primary research question

The first falsifiable question is:

> Given information available after the official close of session `t`, does
> the observed technical and market structure contain causal information about
> favorable versus adverse future price excursion over a bounded daily swing
> horizon?

This is signal-quality research, not execution-PnL research. A positive result
does not claim that a trade can be filled at `Close_t`, that an Open is known,
or that a live strategy is profitable.

The primary estimand is the out-of-sample discrimination and probability
quality of a bounded first-touch barrier outcome for eligible common-share
observations. The estimand is conditional on the pre-registered research
universe, complete causal feature history, and a resolved future path.

Out of scope for V1 are fundamentals, news, macroeconomic data, intraday
ordering, live execution, transaction-cost claims, portfolio sizing, and any
BUY/SELL/EXIT output.

## 3. Signal timing and reference semantics

The signal timestamp is **after the official market close on session `t`**.
Every feature at `t` must be computable using only data with an availability
date less than or equal to `t`:

- `High_t`, `Low_t`, `Close_t`, `Volume_t`;
- official Regular-Market Value when available;
- causal rolling or cross-sectional transformations of those fields;
- point-in-time listing, scope, and ACTIVE state known at `t`.

`Open_t` is optional in the certified research contract and the primary V1
feature set must not depend on it. No feature may use a value from session
`t+1` or later, including a centered rolling calculation, a future-confirmed
pivot timestamped retrospectively, a future universe membership flag, or a
future-fitted scaler/imputer.

The fixed label reference is:

`SIGNAL_REFERENCE_CLOSE = Close_t`

This is a label reference only. It is never called a fill price or execution
price. No claim of execution at `Close_t` is permitted. An eventual
execution-grade layer may use a separately evidenced next-session Open or
another fill model after a separate data and entitlement decision.

No external market benchmark is required for the primary estimand. IHSG or
another index must not be silently assumed. Optional market-context features
may use an explicitly causal equal-weight cross-sectional reference built from
the eligible universe, but that reference is not an execution benchmark and
must remain a separately named feature family.

## 4. Primary research universe

Three universe views will be reported without using future information:

### A. Full valid common-share view

All point-in-time common-share rows with valid ACTIVE H/L/C/Volume and
available feature history. This is the coverage and robustness reference, not
the primary liquidity-conditioned view.

### B. Primary broad causal liquid view

The primary V1 universe is determined separately at each signal date `t`:

1. the security is an in-scope common share and LISTED on `t`;
2. the exact session is officially ACTIVE;
3. at least 20 valid ACTIVE observations exist for that security in the
   trailing 60 official sessions ending at `t`;
4. the median official Regular-Market Value over those observed trailing
   sessions is at least IDR 1,000,000,000;
5. all required feature history is available without forward filling.

The 60-session lookback, 20-observation minimum, and IDR 1 billion threshold
are frozen before any outcome or holdout result is inspected. The rule is
causal and allows IPO warm-up, suspensions, and changing liquidity to affect
eligibility at the correct date. Missing value evidence does not become a
zero; a row failing the value-history requirement is outside this primary
liquidity view and remains visible in the full-valid sensitivity view.

### C. Top-N sensitivity view

As a sensitivity only, rank eligible common shares at each `t` by trailing
60-session median Regular-Market Value and report the top 100 and top 300
groups when the minimum-history rule is met. The ranking is recomputed using
only information available at `t`. Current-active lists, future survival, or a
static 2026 membership list must never define historical membership.

The primary V1 claim is made on view B. View A checks whether the conclusion is
an artifact of a liquidity filter; view C checks concentration sensitivity.
Full-market data remains available for those checks.

## 5. Primary label family and bounded alternatives

The recommended primary family is a **first-touch barrier outcome** because it
maps to the project's eventual invalidation, target, and risk/reward concepts
while remaining falsifiable with daily bars. It is not a trade-PnL label.

### 5.1 Primary barrier definition

The primary horizon is `H = 10` future official exchange sessions. Define a
causal ATR baseline from valid history through `t`:

```text
TR_t = max(High_t - Low_t,
           abs(High_t - Close_(t-1)),
           abs(Low_t - Close_(t-1)))
ATR14_t = simple mean(TR_(t-13) ... TR_t)
SL distance_t = 1.0 * ATR14_t
TP distance_t = 1.5 * ATR14_t
TP level_t = SIGNAL_REFERENCE_CLOSE + TP distance_t
SL level_t = SIGNAL_REFERENCE_CLOSE - SL distance_t
```

The primary candidate requires 14 valid causal TR observations and a positive
SL level. The barrier constants are frozen: `RR=1.5`, `k_sl=1.0`, and no
optimization over alternative values is allowed in the primary run.

For each future official session `u` in `t+1 ... t+10`, inspect only the
ACTIVE research bar for the same security:

- `TP_FIRST` if High_u reaches TP before any SL hit;
- `SL_FIRST` if Low_u reaches SL before any TP hit;
- `AMBIGUOUS_SAME_BAR` if both barriers are reached on the same session before
  an ordering is observable;
- `NO_BARRIER_HIT` if neither barrier is reached by the end of the horizon;
- `UNRESOLVED_PATH` if a required future session is not an eligible valid
  ACTIVE research observation, including UNKNOWN, non-ACTIVE interruption,
  delisting boundary, missing H/L, or insufficient panel horizon;
- `INVALID_BARRIER` if the causal ATR or barrier geometry is invalid.

The primary binary calibration set contains only `TP_FIRST` and `SL_FIRST`.
`NO_BARRIER_HIT`, `AMBIGUOUS_SAME_BAR`, `UNRESOLVED_PATH`, and
`INVALID_BARRIER` are retained as explicit diagnostics and are not silently
converted into wins, losses, or background.

The research-layer normalized excursion fields are descriptive, not execution
returns:

```text
MFE_H = max_u((High_u / SIGNAL_REFERENCE_CLOSE) - 1)
MAE_H = min_u((Low_u / SIGNAL_REFERENCE_CLOSE) - 1)
normalized_close_return_H = (Close_(t+H) / SIGNAL_REFERENCE_CLOSE) - 1
research_R_H = (Close_(t+H) - SIGNAL_REFERENCE_CLOSE) / SL distance_t
```

These fields are emitted only when the required future path is complete. They
must never be described as realized fill PnL.

### 5.2 Bounded secondary label families

The following are pre-specified sensitivity descriptions, not opportunities to
choose the target after seeing results:

- first-touch barrier at `H=5` and `H=20` with the same primary barrier
  geometry;
- MFE/MAE distributions at `H=5`, `H=10`, and `H=20`;
- forward normalized close return at the same three horizons as a continuous
  descriptive baseline.

Only the `H=10` first-touch result is the primary V1 label family. Secondary
horizons are not used to rescue a weak primary result.

## 6. Daily-bar path ambiguity

Daily High/Low does not reveal the intraday order of TP and SL when both are
inside the same bar. The rule is fail-closed:

`AMBIGUOUS_SAME_BAR` is a distinct outcome, never a guessed WIN or LOSS.

Primary treatment: exclude ambiguous observations from the binary probability
calibration denominator, retain them in the outcome ledger, and report their
count and rate by fold, universe, ticker, and date regime. A secondary
sensitivity may show conservative-all-loss and optimistic-all-win bounds, but
those bounds are diagnostics only and cannot be the primary result or used to
tune features.

`NO_BARRIER_HIT` is also retained separately. It is not a failure of the data
gate and is not silently assigned to either binary class. Coverage reports
must distinguish no-touch from ambiguity and from unresolved paths.

## 7. Support/resistance and feature-family proposal

No subjective chart annotations are part of V1. Candidate structure features
must be reproducible and causally timestamped.

### 7.1 Compact primary baseline features

The first baseline feature set is intentionally small:

- close return over 5 and 20 prior/including-current sessions;
- ATR14 divided by Close_t;
- Close_t position within the trailing 20-session High/Low range;
- ATR-normalized distance to the trailing 20-session and 60-session high/low;
- relative Volume_t versus the trailing 20-session median;
- log Regular-Market Value_t relative to its trailing 20-session median;
- observed-session count and security age in sessions at `t`.

All rolling windows are right-aligned and include no date later than `t`.
Where a feature is unavailable, the missing indicator and a training-fitted
imputation rule must be specified before implementation; no future row or
future universe statistic may fill it.

### 7.2 Reproducible S/R family proposal

The bounded experimental structure family may assess:

- prior rolling swing highs/lows over 20 and 60 sessions;
- distance to prior extrema in ATR units;
- close position within prior ranges;
- confirmed fractal/pivot levels with an explicit right-side confirmation
  delay;
- touch count and recency using a fixed ATR-normalized tolerance;
- prior breakout and retest flags whose availability date is the retest or
  confirmation date, never the retrospective pivot date.

A pivot requiring future bars becomes available only after those bars have
elapsed. The implementation must store both the event level and its
availability timestamp. No centered rolling maximum/minimum may be exposed at
the original pivot date.

### 7.3 Other bounded feature families

The following families are candidates, kept separate in ablations:

- price/structure: normalized returns, trend slopes, drawdown, range position;
- momentum: multi-horizon return and one causal bounded oscillator;
- volatility: ATR, realized range, and volatility regime;
- volume/liquidity: relative volume, trading-value ratios, and acceleration;
- market/cross-section: causal breadth, relative strength, and percentile
  ranks from the eligible universe.

No fundamentals, news, macroeconomic variables, neural networks, or enormous
feature zoo are included in the first cycle.

## 8. Temporal split and walk-forward validation

The split is frozen from the exact 1,260-session official calendar before any
outcome prevalence, feature effectiveness, or model result is inspected.

### 8.1 Locked holdout

- development: sessions 1-1008, `2021-04-29 -> 2025-07-14`;
- locked final holdout: sessions 1009-1260, `2025-07-15 -> 2026-07-31`;
- holdout size: 252 official sessions.

The final 20 holdout signal sessions, sessions 1241-1260
(`2026-07-06 -> 2026-07-31`), cannot have a complete 20-session forward label
inside the immutable panel. They remain reserved and untouched; they are
reported as `UNRESOLVED_HORIZON_END` for H=20, not dropped without accounting.
The currently evaluable holdout signal interval for H=20 ends at session 1240
(`2026-07-03`). Extending the calendar later would require a separate
authorized data revision and would not change this frozen split.

The holdout must not be used to select labels, horizons, feature families,
universe thresholds, algorithms, hyperparameters, calibration methods,
probability thresholds, or Opportunity Score mappings.

### 8.2 Development folds

Use three expanding, date-grouped validation folds inside the first 1,008
sessions. The exact index ranges are:

| fold | train signal sessions | purge/embargo gap | validation sessions |
|---|---|---|---|
| F1 | 1-504 (`2021-04-29 -> 2023-05-23`) | 505-524 (`2023-05-24 -> 2023-06-22`) | 525-650 (`2023-06-23 -> 2023-12-27`) |
| F2 | 1-650 | 651-670 (`2023-12-28 -> 2024-01-25`) | 671-796 (`2024-01-26 -> 2024-08-15`) |
| F3 | 1-796 | 797-816 (`2024-08-16 -> 2024-09-12`) | 817-942 (`2024-09-13 -> 2025-03-20`) |

Sessions 943-1008 are a development tail buffer before the locked holdout.
They may be used only by a later pre-registered development refit after fold
decisions are complete; they are not an extra unplanned validation fold.

Every fold keeps all securities from the same signal date grouped. There is no
random split, no per-ticker randomization, and no cross-sectional leakage from
future dates.

## 9. Purge and embargo contract

The maximum future label horizon is `H=20` because H=20 is a frozen secondary
sensitivity even though H=10 is primary. A label observation interval for
signal date `t` is `[t+1, t+H]` in official-session index space.

For a validation block beginning at `v_start`, training candidates satisfy:

```text
train_signal_index <= v_start - H - 1
```

Equivalently, the last `H` sessions immediately before the validation start
are excluded from training. This purge removes training labels whose future
observation interval could overlap the validation block.

The same `H`-session gap is an explicit embargo after the preceding validation
block: no signal in that gap is used for the next fold until its future label
path is outside the next validation boundary. The gap is not filled with
forward values and is counted in fold coverage. The fold table is the canonical
boundary definition; an implementation must assert the index ranges before
fitting anything.

All feature preprocessing, scaling, imputation, feature selection, and model
fitting are fit only on the fold's training rows. A label path must be complete
before its row is admitted to a training or validation metric denominator.

## 10. Primary metrics and reporting

Metrics are reported by fold, date regime, universe view, ticker coverage, and
pooled out-of-fold summary. Raw accuracy is not a primary objective.

### Discrimination and ranking

- primary: PR-AUC for `TP_FIRST` versus `SL_FIRST`;
- secondary: ROC-AUC;
- top-quintile and top-decile outcome rates;
- monotonicity of resolved outcome rate across fixed score buckets.

### Probability quality

- Brier score;
- reliability curve with fixed 10-bin boundaries defined from training data;
- expected calibration error using the same pre-declared bins;
- fold-to-fold calibration dispersion.

### Economic-like signal quality

- MFE and MAE distributions;
- mean research-normalized R under the declared barrier semantics;
- barrier outcome rate by score bucket.

These are research diagnostics, not execution returns or PnL.

### Coverage and data quality

- candidate count;
- resolved `TP_FIRST`/`SL_FIRST` count;
- `NO_BARRIER_HIT` count;
- `AMBIGUOUS_SAME_BAR` count/rate;
- `UNRESOLVED_PATH` and `INVALID_BARRIER` count/rate;
- number of dates and tickers represented;
- primary liquidity-universe inclusion rate.

The primary comparison is mean fold PR-AUC against the pre-registered
base-rate and momentum baselines. A model is not considered a research
advancement unless it is directionally better than both simple baselines in at
least two of the three development folds, with no silent coverage loss or
ambiguity relabelling. This is a development decision rule only; it does not
permit holdout tuning.

## 11. Baselines and bounded model families

The baselines are frozen before advanced modelling:

1. **Base-rate baseline:** training-fold resolved `TP_FIRST` prevalence as a
   constant probability for that fold.
2. **Momentum baseline:** the causal 20-session close return as a one-dimensional
   score, with fold-fitted probability calibration for probability metrics.
3. **Trend/structure baseline:** a fixed small logistic model using the compact
   baseline features listed in section 7.1.
4. **Optional bounded challenger:** one HistGradientBoosting-style tree model
   using the same frozen baseline feature table.

No neural network, AutoML search, dozens of algorithms, or unconstrained
feature search is permitted in V1. Hyperparameters must be fixed in a written
Stage 3 plan before any fit and may not be selected from the locked holdout.

## 12. Calibration and semantic separation

The raw model score and calibrated probability are separate artifacts. The
primary calibration method is Platt/logistic calibration fit chronologically
on an internal tail of each training fold. Isotonic calibration is a declared
sensitivity only when the calibration slice has sufficient examples of both
primary classes; it is not selected from holdout performance.

Calibration data must be later than the model-fit data and earlier than the
validation block. All calibration transformations are fit from training data
only. The final holdout is calibrated only by a method frozen from development.

The eventual structured output must preserve:

- `P_TP_BEFORE_SL`: calibrated research probability;
- `RESEARCH_EXPECTED_R`: barrier-semantics expectation, not execution PnL;
- `OPPORTUNITY_SCORE`: a separately specified composite that may incorporate
  probability, RR, setup quality, and liquidity;
- `ESTIMATE_RELIABILITY`: a separate stability/coverage/calibration assessment.

Probability is not Opportunity Score. Opportunity Score is not Estimate
Reliability. No opaque confidence field may collapse them.

## 13. Freeze register and next decision

The following are frozen for V1:

- question: causal technical/market structure for bounded future excursion;
- timestamp: after official close at `t`;
- primary reference: `SIGNAL_REFERENCE_CLOSE`;
- primary label: first-touch barrier, H=10, `RR=1.5`, `k_sl=1.0`;
- ambiguity: explicit `AMBIGUOUS_SAME_BAR`, excluded from primary binary
  calibration and retained diagnostically;
- primary universe: broad causal liquid view B;
- sensitivity universes: full valid view A and causal top-100/top-300 view C;
- holdout: sessions 1009-1260, exact dates above;
- development: sessions 1-1008 with the three exact walk-forward folds;
- maximum purge/embargo horizon: 20 sessions;
- primary metric: mean fold PR-AUC with fixed baseline comparisons;
- baseline set: base rate, momentum, fixed logistic trend/structure, one
  bounded tree challenger;
- Open: never required by primary V1 features and never synthesized.

Decision status for this document is `STAGE2_SPEC_GO` only after the separate
adversarial review records no material unresolved finding. If approved, the
next phase is **STAGE 3 - LABEL / FEATURE PIPELINE + BASELINE MODELS**. Stage 3
is not started by this document.

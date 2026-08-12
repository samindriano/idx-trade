# Expected Payoff V0 — Frozen Historical Feasibility Specification

Date: 2026-08-12 (Asia/Jakarta)

Branch: `research/idx-expected-payoff-v0-feasibility`

Decision: `EXPECTED_PAYOFF_V0_HISTORICAL_DIAGNOSTIC_AUTHORIZED_FROZEN`

## 1. Purpose

Expected Payoff is a separate layer from Alpha Ranking, Probability, Path Risk,
Decision/Sizing, and Execution.

This V0 asks only:

> Do the already-frozen O2 out-of-fold historical scores contain a stable
> cross-sectional relationship with the magnitude of a causal, executable
> fixed-horizon future price payoff?

V0 is a **feasibility diagnostic, not a payoff model**. It may justify a later
Expected Payoff V1 specification, but it cannot itself create a production
payoff estimate, trade rule, filter, sizing rule, or promotion decision.

## 2. Protected boundaries

Hard constraints:

- use historical-development evidence only;
- do not read, derive, join, inspect, or score any fresh-forward outcome after
  `2026-07-31`;
- do not touch the active O2 `1/100` forward counter, score ledger, outcome
  vault, runtime, scheduler, or frontend;
- do not retrain, refit, tune, or modify O2, V3-B, V2, O2.1, or Probability;
- do not call a provider or network source;
- do not repair or synthesize Open/Close data;
- do not search alternate entries, exits, horizons, payoff normalizations,
  bins, metrics, or thresholds after seeing the result;
- do not fit any Expected Payoff model in V0.

The old Stage-5 ranking holdout is not an independent validation set for this
lane. This is explicitly reused historical-development evidence and must never
be described as new OOS proof.

## 3. Frozen parent evidence

The runner must fail closed unless it verifies the accepted O2 historical
artifacts and the underlying data identities.

Required O2 parent:

- branch lineage: `research/idx-ranking-ohlcv-o2-geometry-v1`;
- O2 decision: `O2_SURVIVOR`;
- O2 artifact manifest SHA-256:
  `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`;
- O2 fold predictions SHA-256:
  `fe02c0c743e7bfc5a57b1c8e731c5685a4bff5f9854f910f88703b15a6ca8f0c`;
- exact O2 common-support key SHA-256:
  `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- O2 feature-order SHA-256:
  `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`.

Required preserved source identities:

- immutable model-safe panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official exchange calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- PIT security master SHA-256:
  `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`;
- accepted Yahoo+TradingView Open panel SHA-256:
  `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab`;
- accepted Open provenance SHA-256:
  `90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687`;
- V3-B training table SHA-256:
  `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe`;
- V3-B final manifest SHA-256:
  `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9`.

Do not hard-code expected V0 row counts. Derive them from the verified parents.

## 4. Frozen population

Start only from the accepted O2 historical `fold_predictions.parquet` rows for
model `O2_OPEN_GEOMETRY` on the same six historical validation folds.

Requirements:

- one unique O2 prediction per `ticker/date/fold` validation key;
- exact original O2 score; do not rescore or refit O2;
- signal session/date must remain historical and no later than the accepted
  O2 historical boundary;
- future data needed to resolve the V0 payoff must be no later than
  `2026-07-31`.

V0 is evaluated on the subset whose frozen payoff can be resolved under the
rules below. Every excluded parent row must remain in a coverage ledger with
one explicit exclusion reason.

## 5. Frozen causal payoff contract

The O2 signal is known only after the official close of signal session `t`.
Therefore `Close_t` is **not** used as the executable entry.

### Entry

`ENTRY = Open_(t+1)`

where `t+1` is the next official IDX session in the verified calendar.

The entry Open must be an already-accepted, finite, positive Open with accepted
provenance. No interpolation, carry-forward, adjusted-price substitution, or
new provider lookup is allowed.

If the stock is not defensibly Regular-Market executable at `t+1`, or the
accepted Open is unavailable/invalid, the row is unresolved and excluded from
payoff metrics with an explicit reason.

### Exit

`EXIT = Close_(t+10)`

where `t+10` is the tenth official IDX session after the signal session.

The exit Close must be the preserved raw execution Close, finite and positive,
and the row must be defensibly resolvable under the existing PIT/tradability
contract. Missing or unresolved exit evidence is never filled.

### Normalization

Use the signal-time ATR already represented by the canonical V3-B training
row:

`ATR14_t = Close_t * atr14_over_close_t`

and require `ATR14_t > 0` and finite.

Primary continuous payoff:

`payoff_atr_gross = (Close_(t+10) - Open_(t+1)) / ATR14_t`

Secondary human-readable payoff:

`payoff_pct_gross = Close_(t+10) / Open_(t+1) - 1`

Also persist the non-gating entry-gap diagnostic:

`entry_gap_pct = Open_(t+1) / Close_t - 1`

The word `gross` is mandatory: V0 does not include brokerage fees, taxes,
spread, slippage, partial fills, or market impact and therefore must not be
reported as net trading PnL.

## 6. Corporate-action / raw-price integrity

Raw execution prices must not create fake payoff jumps across price-scale
corporate actions.

Before computing payoff, audit and reuse the repository's existing canonical
corporate-action evidence/resolver. A row whose `(t+1 .. t+10)` window crosses
a known **price-scale-changing** corporate action (for example split/reverse
split or another event that makes the raw entry/exit price ratio mechanically
non-comparable) must be excluded with reason `PRICE_SCALE_CA_CROSSED` unless an
already-accepted canonical economic adjustment exists in the repository and
can be applied without any new inference or provider call.

Do not invent a new adjustment factor in this lane. If the repository cannot
prove a safe canonical treatment for such a window, exclude it fail-closed.

Cash distributions are outside the V0 target: this V0 is explicitly a
**price-payoff** diagnostic, not total shareholder return.

## 7. Frozen coverage / data-readiness gate

Persist exact counts globally, by fold, by year, and by exclusion reason.

`EXPECTED_PAYOFF_V0_DATA_READY` requires all of:

1. resolved payoff rows / accepted O2 OOF parent rows >= `0.90` globally;
2. resolved payoff rows / parent rows >= `0.85` in every fold;
3. at least `80` signal sessions per fold have at least `30` resolved tickers
   and non-constant O2 score and payoff, making the session eligible for the
   cross-sectional metrics below;
4. no parent hash/provenance/calendar/feature identity mismatch;
5. no post-2026-07-31 data/outcome access.

If any data-readiness requirement fails, verdict is
`EXPECTED_PAYOFF_V0_DATA_BLOCKED`; do not reinterpret a partial result as a
signal failure.

## 8. Frozen primary feasibility metrics

The unit of cross-sectional evaluation is the **signal session**, not a pooled
row correlation across years.

For each metric-eligible signal session:

### 8.1 Session IC

Compute Spearman rank correlation between frozen O2 score and
`payoff_atr_gross` across resolved tickers.

Call it `session_ic_atr`.

### 8.2 Session top-minus-bottom payoff spread

Within the session, stable-sort by `(O2 score, ticker)` and split rows into ten
approximately equal-count bins using deterministic ordinal positions. `D10`
is highest score and `D1` is lowest score.

Compute:

`session_d10_minus_d1_mean_payoff_atr = mean(D10 payoff_atr_gross) - mean(D1 payoff_atr_gross)`

No alternative bin count is allowed in this V0.

### 8.3 Fold aggregates

For each of the six frozen O2 folds persist at minimum:

- eligible signal-session count;
- median and mean `session_ic_atr`;
- standard deviation of `session_ic_atr`;
- mean / std IC ratio as descriptive only;
- median and mean `session_d10_minus_d1_mean_payoff_atr`;
- D1 and D10 realized payoff mean, median, q25, q75;
- same session IC and D10-D1 diagnostics for `payoff_pct_gross` as secondary,
  non-gating evidence.

Also persist full decile realized payoff summaries and a decile-index versus
realized-payoff monotonicity diagnostic, but these are non-gating.

## 9. Frozen feasibility gate

If and only if `EXPECTED_PAYOFF_V0_DATA_READY` passes, V0 receives
`EXPECTED_PAYOFF_V0_FEASIBILITY_GO` when **all** conditions below hold:

1. median across the six fold-median `session_ic_atr` values is strictly `> 0`;
2. q25 across the six fold-median `session_ic_atr` values is strictly `> 0`;
3. at least `4/6` folds have positive median `session_ic_atr`;
4. median across the six fold-mean D10-D1 ATR-payoff spreads is strictly `> 0`;
5. at least `4/6` folds have positive mean D10-D1 ATR-payoff spread.

Otherwise, if data readiness passed, verdict is
`EXPECTED_PAYOFF_V0_NO_SIGNAL`.

There is deliberately no post-result magnitude threshold, p-value rescue,
horizon change, alternate entry, alternate normalization, or alternate binning
allowed in V0.

## 10. Required artifacts

Persist and hash-manifest at minimum:

- `preflight_contract.json`;
- `parent_o2_predictions_identity.json`;
- `payoff_row_coverage.csv` with every parent O2 OOF row and its resolved /
  exclusion status;
- `resolved_payoff_rows.parquet`;
- `coverage_summary.csv`;
- `coverage_by_fold.csv`;
- `coverage_by_year.csv`;
- `exclusion_reasons.csv`;
- `session_metrics.csv`;
- `fold_metrics.csv`;
- `decile_payoff_summary.csv`;
- `aggregate_metrics.json`;
- `survivor_decision.json`;
- `artifact_manifest.json`.

Record stable row-key SHA-256 for the parent O2 OOF keys and resolved V0 payoff
keys. Record source/provenance hashes and whether any corporate-action windows
were excluded.

The manifest and summary must explicitly contain:

- `fresh_forward_outcomes_accessed=false`;
- `forward_outcome_access_marker_written=false`;
- `provider_calls=false`;
- `o2_model_modified=false`;
- `payoff_model_fit=false`.

## 11. Tests / fail-closed checks

At minimum test:

- signal `t` maps to entry session `t+1` and exit session `t+10` by the exact
  verified official calendar;
- signal Close is never used as entry;
- missing/invalid next Open is excluded, never filled;
- missing/invalid exit Close is excluded, never filled;
- ATR normalization is exactly the frozen formula;
- a price-scale corporate-action crossing is excluded/fail-closed;
- future date beyond `2026-07-31` is rejected;
- O2 scores are consumed from the accepted fold-prediction artifact and not
  recomputed;
- deterministic session deciles are reproducible under score ties;
- coverage gate and feasibility gate boundary cases;
- no fresh-forward marker/outcome/runtime path is touched.

Run focused tests and the full repository pytest suite.

## 12. One-shot stop rule

Run this frozen V0 exactly once after implementation.

If verdict is `EXPECTED_PAYOFF_V0_DATA_BLOCKED`:

- stop for independent review;
- do not lower coverage thresholds or silently change the payoff target.

If verdict is `EXPECTED_PAYOFF_V0_NO_SIGNAL`:

- close this exact V0 hypothesis;
- do not rescue it by trying Close_t entry, H5/H20, other normalizations,
  winsorization, different bins, or subgroup filters.

If verdict is `EXPECTED_PAYOFF_V0_FEASIBILITY_GO`:

- persist artifacts and stop for independent ChatGPT review;
- **do not automatically train Expected Payoff V1**;
- any V1 model family, target, baseline, loss, fold contract, or promotion rule
  requires a new explicit preregistration and authorization.

This specification is frozen before V0 payoff results are observed.

# Ranking V3 Structure-Lite Specification V1

Status: **FROZEN FOR SPECIFICATION / DEFINITION AUDIT ONLY**

Date: 2026-08-10

Repository: `samindriano/idx-trade`

Specification branch: `research/idx-ranking-v2-spec-v1`

Specification source head: `d1c1d21f3728610a3bb82d74ee0d4618499b4f6e`

This document freezes the definition of the V3-B Structure-Lite research
candidate. It does not contain fitted-model, score, F1-F4 outcome, F5/F6, or
fresh-forward results. No runtime was started while this specification was
written.

## 1. Authorization and research question

This specification follows:

`coordination/handoffs/IDX-RANKING-V3-STRUCTURE-LITE-SPEC.md`

The authorized scope is a specification/definition audit only. The following
remain prohibited under this document:

- fitting or scoring any model;
- inspecting V2F5 or V2F6 outcomes;
- accessing reserved V2 forward outcomes after 2026-07-31;
- writing `FORWARD_OUTCOME_ACCESS_STARTED`;
- rescuing or reopening V3-A Recency;
- starting V3-C, calibration, Stage 6, `IDX-VAL-002`, execution-PnL,
  paper/live work, or a main-branch merge.

### 1.1 Single falsifiable hypothesis

> Does a compact, causal representation of support/resistance and price
> structure geometry add robust same-date ranking information beyond the exact
> frozen V2 `HGB_XS_MARKET` 25-feature representation?

The hypothesis is about incremental representation value. It is not a claim
that a chart overlay, hand-built score, empirical probability, or trading
decision layer is valid.

### 1.2 Candidate budget

The future discovery run has exactly two candidates:

1. the exact frozen V2 `HGB_XS_MARKET` control;
2. one fixed Structure-Lite candidate defined in Section 4.

No second Structure-Lite variant is preregistered. The bundle is deliberately
small because the prior V3-A experiment already closed its bounded recency
question without promotion. No ablation or parameter rescue is authorized
under this hypothesis.

## 2. Audit of the V2 representation

The exact V2 control remains `HGB_XS_MARKET` with these 25 ordered features:

### 2.1 Security-level cross-sectional features

1. `xs_rank_close_return_5`
2. `xs_rank_close_return_20`
3. `xs_rank_atr14_over_close`
4. `xs_rank_close_position_20`
5. `xs_rank_distance_high_20_atr`
6. `xs_rank_distance_low_20_atr`
7. `xs_rank_distance_high_60_atr`
8. `xs_rank_distance_low_60_atr`
9. `xs_rank_relative_volume_20`
10. `xs_rank_log_regular_value_relative_20`

### 2.2 Same-date market context

11. `market_primary_liquid_count`
12. `market_breadth_return_5_positive`
13. `market_breadth_return_20_positive`
14. `market_median_close_return_5`
15. `market_median_close_return_20`
16. `market_median_atr14_over_close`
17. `market_median_close_position_20`
18. `market_median_relative_volume_20`
19. `market_median_log_regular_value_relative_20`

### 2.3 Market-relative features

20. `market_relative_close_return_5`
21. `market_relative_close_return_20`
22. `market_relative_atr14_over_close`
23. `market_relative_close_position_20`
24. `market_relative_relative_volume_20`
25. `market_relative_log_regular_value_relative_20`

The V2 representation already contains raw rolling high/low distances,
20-session range position, ATR, returns, and relative volume. Structure-Lite
therefore does not add another generic rolling range, momentum, or volatility
library. Its incremental claim is limited to *historical level identity and
geometry*: clustered causal pivots, separated interactions with those levels,
role reversal, and a current breakout/retest state.

The V2 feature code and specification remain authoritative:

- `src/idx_trade/research_v2_features.py`
- `src/idx_trade/research_v2_models.py`
- `src/idx_trade/research_v2_validation.py`
- `docs/RANKING_V2_RESEARCH_SPEC_V1.md`

V2 same-date percentile ranks, market-context construction, missing-value
handling, date/ticker uniqueness, and the exact HGB preprocessing are not
changed by this document.

## 3. Legacy archive audit and salvage boundary

The read-only archive source was:

- repository: `samindriano/past-models-indo-stock`;
- branch: `frontend/indo-stock-lookup-support-resistance`;
- archive head: `b10f1f619d99590028823addb2cd497333aff20f`;
- preserved source snapshot: `snapshots/indo-stock-lookup-support-resistance/`.

The archive note explicitly says that the snapshot preserves the earlier
model-decision layer and is not evidence that the underlying model passed
validation. The following boundary is frozen:

| Legacy material | Structure-Lite disposition |
|---|---|
| Window extrema and pivot candidates | Salvage only as trailing, left-only causal candidates. |
| Centered pivot windows (`center=True`) | Prohibited: they use future bars to confirm a pivot. |
| Historical level touches | Salvage after redefining them with OHLC band intersection and minimum session separation. |
| Level clustering | Salvage with a deterministic, price/ATR graph rule; no strength score. |
| Level recency/age | Salvage as official-session distance from the latest pivot in the selected cluster. |
| Role-reversal candidates | Salvage only after an observed causal crossing and an in-window retest through the current historical boundary. |
| Breakout/retest labels | Salvage as current-bar causal state; no future confirmation bar. |
| Volume confirmation | Salvage only from current or prior bars and a trailing prior-volume baseline. |
| Chart anchors and frontend rendering | Not a model feature or validation artifact. |
| Snapshot-aligned boosts, selection/strength scores, hand weights | Prohibited. |
| `actual_up`, realized returns, routed tests, range-backtest buckets | Prohibited; outcome-conditioned. |
| Ticker/setup empirical probabilities, horizon weights, investment verdicts | Prohibited; downstream decision/scoring layer. |

In particular, the legacy implementation used centered rolling windows for
pivots, counted price-only touches without the new separation contract, and
combined geometry with snapshot alignment and hand-tuned scores. Those details
are historical implementation facts, not V3-B evidence or frozen parameters.

## 4. Frozen Structure-Lite representation

All features are calculated separately per security and are appended after the
exact 25 V2 columns in the order below. All numeric operations use float64.
All session distances use the official exchange-session index, never calendar
days.

### 4.1 Fixed constants

The single candidate uses these constants, fixed before any V3-B outcome is
viewed:

- pivot lookback `P = 5` sessions;
- level candidate lookback `L = 60` sessions;
- role-reversal/event history `R = 120` sessions;
- touch minimum separation `S = 3` sessions;
- retest horizon `B = 10` sessions after the triggering breakout;
- volume baseline `V = 20` prior sessions;
- pivot-cluster price tolerance `0.50 * max(ATR14_p, ATR14_q)`;
- touch-band half-width on session `j`:
  `max(0.50 * ATR14_j, 0.01 * abs(level))`.

The ATR14 values and all prices must come from the same split-consistent
technical-price frame. A non-positive or non-finite ATR invalidates that
calculation rather than being replaced by a constant.

### 4.2 Output columns

| Order | Feature | Meaning |
|---:|---|---|
| 26 | `structure_support_distance_atr` | Current close distance above the nearest valid support, divided by `ATR14_t`. |
| 27 | `structure_resistance_distance_atr` | Current close distance below the nearest valid resistance, divided by `ATR14_t`. |
| 28 | `structure_support_touch_count_60` | Separated historical OHLC interactions with the selected support cluster in the prior 60 sessions. |
| 29 | `structure_resistance_touch_count_60` | Separated historical OHLC interactions with the selected resistance cluster in the prior 60 sessions. |
| 30 | `structure_nearest_level_age_sessions` | Official-session age of the nearest selected support/resistance cluster's newest pivot. |
| 31 | `structure_role_reversal_count_120` | Count of completed causal level role reversals across current clusters in the prior 120 sessions. |
| 32 | `structure_breakout_retest_state` | Signed current event code: `-2`, `-1`, `0`, `+1`, or `+2`. |
| 33 | `structure_breakout_volume_confirmed` | Boolean `1/0` for volume confirmation of the triggering breakout for a nonzero event state. |

The nearest level cluster count is deliberately not an output feature. It is
used only to make cluster construction auditable; adding it would be a ninth
feature and is not needed to test the single geometry hypothesis.

### 4.3 Point-in-time order of operations

For a signal row `(ticker, t)`, the level inventory is built from sessions
`[t-L, t-1]`. The current session `t` is never allowed to create, merge,
select, or count a support/resistance level. Current `High_t`, `Low_t`,
`Close_t`, `Volume_t`, and `ATR14_t` may be used only for the explicitly
defined current distance and event calculations below, because they are
available at the after-close signal timestamp.

No future confirmation bar is used. A pivot, cluster, touch, role reversal,
breakout, and retest must be computable using data at or before the feature's
signal timestamp.

### 4.4 Causal pivot candidates

For each prior session `p`, a high pivot candidate exists when:

- `High_p` is finite and positive;
- `ATR14_p` is finite and positive;
- `High_p = max(High_{p-P+1}, ..., High_p)`;
- all required values in that left-only window are valid.

A low pivot is symmetric using `Low_p = min(Low_{p-P+1}, ..., Low_p)`.

This is a causal trailing pivot, not the legacy centered local-extrema test.
Ties are retained as candidates and are resolved only by the deterministic
clustering and selection rules below. If fewer than `P` valid sessions exist,
no pivot candidate is emitted.

### 4.5 Level clustering and support/resistance selection

1. Collect all high and low pivot candidates in `[t-L, t-1]`.
2. Build an undirected graph within each pivot side. Two candidates `p` and
   `q` share an edge when their absolute price difference is no greater than
   `0.50 * max(ATR14_p, ATR14_q)`.
3. A cluster is a connected component. Its level is the median member price;
   its newest pivot is the newest member date. Components are deterministic
   under stable `(session_index, price, side)` ordering.
4. A cluster is support when its level is `<= Close_{t-1}` and resistance
   when its level is `> Close_{t-1}`. A level exactly equal to the prior close
   is support by this rule, never both sides.
5. Select the nearest support as the greatest support level and the nearest
   resistance as the smallest resistance level. Ties use newest pivot, then
   lower session index, then lower level for support / higher level for
   resistance. No distance, cluster strength, snapshot, or outcome score is
   used to choose a level.

The selected support distance is
`(Close_t - support_level) / ATR14_t`. The selected resistance distance is
`(resistance_level - Close_t) / ATR14_t`. A negative distance is retained if
the current close has crossed the prior selected level; it is not clipped.

The nearest-level age compares the two selected levels using their
prior-close, ATR-normalized distances. The smaller distance wins; an exact tie
chooses support. Age is `session_index(t) - session_index(newest_pivot)`.

### 4.6 Touch counting

For a selected level and each prior session `j` in `[t-60, t-1]`, a touch is
possible when valid `High_j` and `Low_j` intersect the band

`[level - w_j, level + w_j]`, where
`w_j = max(0.50 * ATR14_j, 0.01 * abs(level))`.

The touch is retained by a chronological greedy filter: keep the earliest
touch, then retain a later touch only when its official-session index is at
least `S` sessions after the last retained touch. This prevents adjacent-bar
inflation. Missing OHLC/ATR means no touch for that session and is reported in
coverage diagnostics. Current session `t` is never a historical touch.

### 4.7 Role reversal

For each current cluster whose newest pivot lies inside the prior 120-session
history, scan only sessions through `t-1` and after the cluster's relevant
pivot. A completed reversal requires:

- an old-side close at or within the level band;
- a close crossing beyond the level band to the new side;
- within the next `B=10` official sessions, an OHLC touch of the level band;
- the retest close remains on the new side of the band.

An upside crossing followed by a successful retest is resistance-to-support;
a downside crossing followed by a successful retest is support-to-resistance.
The current session is not eligible to complete the count. Each current
cluster contributes at most one completed reversal per direction in the
`R=120`-session window. No reversal is inferred from a pivot alone, row
presence, a chart label, a Yahoo outcome, or an unconfirmed intraday wick.

`structure_role_reversal_count_120` is the sum of these completed reversals
across the current causal clusters. It is zero when valid clusters exist but
no reversal is found.

### 4.8 Breakout, retest, and volume confirmation

The event state is evaluated against the selected prior-session levels:

- `+1`: `Close_{t-1}` was at or below the selected resistance band and
  `Close_t` is strictly above it: causal upside breakout at `t`.
- `-1`: `Close_{t-1}` was at or above the selected support band and `Close_t`
  is strictly below it: causal downside breakdown at `t`.
- `+2`: within `B=10` sessions after a prior `+1` breakout, current
  `Low_t` touches the breakout level band and `Close_t` finishes strictly
  above it: successful upside retest at `t`.
- `-2`: symmetric successful downside retest after a prior `-1` breakdown.
- `0`: no current breakout/retest event, including a failed or invalidated
  prior event.

If both sides could produce an event on the same date, choose the side with
the smaller prior-close normalized distance; an exact tie chooses support for
downside before resistance for upside. A breakout must use close confirmation;
an intraday high/low crossing alone is not an event. Failed breakouts are not
converted into a positive or negative score and produce state `0` after
invalidation.

For a nonzero state, the triggering breakout session is `t` for `+1/-1` and
the earlier breakout session for `+2/-2`. Volume is confirmed when the
triggering session has finite positive regular-market volume and:

`Volume_trigger >= 1.5 * median(Volume_{trigger-20}, ..., Volume_{trigger-1})`

with at least 10 valid positive prior volumes. Otherwise
`structure_breakout_volume_confirmed = 0`. If there is no valid structure
context, both event features are missing; if valid context exists and there is
no event, state is `0` and the boolean is `0`. The volume baseline never
includes the triggering/current bar.

## 5. Missing values, numerical safety, and semantics

- No valid pivot/level, insufficient history, invalid ATR, or invalid required
  OHLC produces `NaN` for the affected distance/count/age/role feature.
- Event state and volume are `NaN` when no valid structure context exists;
  otherwise no event is the explicit `0` state and `0` volume flag.
- `NaN` is preserved into the existing training-only median-imputer contract;
  no zero, forward-fill, nearest-level invention, or cross-ticker fill is
  allowed.
- Non-finite prices, negative volume, duplicate `(ticker, date)` rows,
  misordered sessions, and inconsistent split semantics fail closed.
- Decimal comparisons use float64 with no price rounding. Display tick
  rounding from the legacy frontend is not part of this feature contract.
- The feature builder must prove that a one-bar future append cannot change
  any already-materialized row, except for a separately documented cache
  revision caused by an upstream source revision. Future rows must not be
  used to backfill prior pivots or levels.

## 6. Data and immutable-cache architecture

The V3-B prepared cache must be a new immutable artifact. It must not overwrite
or expand the frozen V2 prepared cache.

The preferred construction is:

1. Read the frozen signal-research HLCV panel and its manifest.
2. Recompute the exact V2 25-feature frame through the existing V2 feature
   pipeline, not by retyping columns.
3. Derive the eight causal Structure-Lite columns from the same split-consistent
   HLCV rows and official session calendar.
4. Join the causal frame to the immutable V2 eligible rows on exact
   `(ticker, signal_date, session_index)`.
5. Preserve the exact V2 row order, labels, eligibility, and universe.

Pinned existing lineage at specification time:

- V2 prepared table:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet`
- V2 prepared table SHA-256:
  `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`
- V2 prepared manifest SHA-256:
  `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`
- signal-research panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- signal-research manifest SHA-256:
  `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`
- official calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- security master SHA-256:
  `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`

The future V3-B cache manifest must also pin the source commit, feature-order
hashes, calendar/security hashes, model/preprocessing identity, and the exact
legacy-audit source branch/head. A missing, ambiguous, changed, duplicated, or
misaligned artifact is a hard stop.

Required future cache proofs:

- exact row identity and order against V2;
- exact label and fold identity against V2;
- byte/hash inventory for every input and output artifact;
- V2 25-feature equality on joined rows under the existing equivalence
  tolerance;
- per-column structure coverage and missingness by fold/date/ticker;
- no current-bar/future-bar dependency test;
- no duplicate or orphan join rows.

## 7. Future discovery and validation contract

This section is a future run contract only. It was not executed in this audit.

### 7.1 Folds

Run only V2F1-V2F4:

- F1: train sessions 1-504, gap 505-524, validation 525-624;
- F2: train 1-624, gap 625-644, validation 645-744;
- F3: train 1-744, gap 745-764, validation 765-864;
- F4: train 1-864, gap 865-884, validation 885-984.

V2F5 and V2F6 remain sealed and must not be scored. No date after
2026-07-31 may be inspected through a V2 forward-outcome artifact.

### 7.2 Control equivalence gate

Before reading any Structure-Lite candidate metric, rerun the exact V2 control
on V2F1-V2F4 and compare to immutable V2 artifacts. The gate must prove:

- exact eligible row identity, order, ticker/date, labels, and fold boundaries;
- exact 25-feature order and values under the existing numeric tolerance;
- row-level ranking score equality under the existing research tolerance;
- prevalence;
- PR-AUC and `PR-AUC - prevalence`;
- ROC-AUC;
- Q1 TP rate, Q5 TP rate, Q5-Q1 spread;
- top-decile TP rate and lift.

If equivalence fails, stop immediately and do not inspect Structure-Lite
metrics. Do not weaken tolerance or regenerate the frozen V2 reference to get
a pass.

### 7.3 Metrics and absolute sanity gate

Use the exact V2 metrics and ranking score definition. Required per-fold and
aggregate metrics are prevalence, PR-AUC, PR-AUC minus prevalence, ROC-AUC,
Q1/Q5 TP rates, Q5-Q1 TP-rate spread, and top-decile TP rate/lift.

The candidate absolute discovery gate is fixed as:

1. all required metrics are finite;
2. median PR-AUC minus prevalence is strictly positive;
3. PR-AUC minus prevalence is positive in at least 3 of 4 folds;
4. median ROC-AUC is greater than `0.50`;
5. ROC-AUC is greater than `0.50` in at least 3 of 4 folds;
6. median Q5-Q1 is strictly positive;
7. Q5-Q1 is positive in at least 3 of 4 folds.

Coverage and missingness are mandatory diagnostics, not a reason to silently
drop rows. Any data, provenance, fold, or cache-contract failure is a hard
`KILL` regardless of metric values.

### 7.4 Paired promotion gate

Structure-Lite may pass discovery only if it passes the absolute gate and all
of these fixed paired rules versus exact V2 control:

1. median PR-AUC-delta improvement is at least `+0.001`;
2. q25 PR-AUC-delta improvement is non-negative;
3. worst-fold PR-AUC-delta improvement is non-negative;
4. candidate is not below control on PR-AUC delta in at least 3 of 4 folds;
5. median ROC-AUC change is no worse than `-0.005`;
6. median Q5-Q1 change is no worse than `-0.005`;
7. candidate is not below control on Q5-Q1 in at least 3 of 4 folds.

Top-decile lift, q25/worst-fold behavior, late-discovery behavior, and
coverage/missingness are mandatory reports and cannot rescue a failed primary
gate.

### 7.5 Decision rule

- `KILL`: contract/provenance failure, non-finite required metric, or absolute
  gate failure.
- `KEEP_DIAGNOSTIC`: clean finite candidate that fails the paired gate.
- `PROMOTE_FOR_NEXT_RESEARCH_STEP`: clean candidate that passes both discovery
  gates. This does not authorize implementation, forward access, probability,
  execution, or trading.

If Structure-Lite is not promoted, the deterministic decision is
`V3_B_STRUCTURE_LITE_KILL_KEEP_V2_CONTROL`. There is no rescue variant.

## 8. Provenance, artifacts, and ledger contract

The future run output must include, at minimum:

- immutable input manifest and SHA-256 inventory;
- new prepared Structure-Lite table and manifest;
- exact V2 control equivalence report;
- per-fold control and Structure-Lite metrics;
- paired deltas and aggregate q25/worst/late diagnostics;
- feature coverage/missingness report;
- runtime profile and deterministic environment;
- candidate verdict and decision;
- test result and source commit;
- hypothesis-ledger row with spec/cache/model/artifact hashes.

Only actually run candidates increment the cumulative denominator. This audit
pre-registers one control slot and one Structure-Lite slot but does not count
either as evaluated. No result values may be added to the ledger by this
specification task.

## 9. Required tests before any future run

The implementation must add focused tests for:

1. no future-bar dependence in pivots, levels, touches, age, role reversal,
   breakout, retest, and volume;
2. rejection of centered/look-ahead pivot confirmation;
3. current-bar close breakout semantics;
4. split-adjusted/technical-price and raw-price contract behavior;
5. deterministic clustering, ties, exact-equality side assignment, and stable
   ordering;
6. no-level, single-level, insufficient-history, invalid-ATR, and invalid-HLCV
   behavior;
7. minimum touch separation and adjacent-touch inflation prevention;
8. role reversal only after crossing plus causal retest;
9. breakout/retest state and volume baseline boundaries;
10. exact V2 row/feature equivalence after the cache join;
11. duplicate/orphan/misaligned cache rows fail closed;
12. F5/F6 and fresh-forward hard blocks;
13. provenance/hash mismatch fail closed;
14. one-bar append invariance for already-materialized rows.

Tests must not use realized outcomes to construct features or expected geometry.

## 10. Stop condition

This specification audit ends after the spec, checkpoint, handoff, ledger
continuity, and status documentation are committed and pushed. The next action
is independent ChatGPT review. A separate authorization is required before any
Structure-Lite implementation or F1-F4 discovery run.

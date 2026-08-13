# Clean V2 Open Alpha — Frozen Preregistration

Date: 2026-08-13 (Asia/Jakarta)
Status: **PREREGISTERED_OUTCOME_BLIND_AUDIT_COMPLETE_REVIEW**
Branch: `research/idx-v2-open-alpha-prereg-v1`
Parent research pass: `research/idx-v2-open-alpha-research-pass-v1@504c51bad25517bf496ee14856be704935d0f5d4`

## Scientific boundary

This checkpoint freezes one clean historical parent and exactly two Open
challengers. It does not authorize fitting, scoring, target loading, provider
calls, protected forward access, model/counter changes, or canonical artifact
replacement.

The accepted clean historical parent is V2 `HGB_XS_MARKET`. V3-B is closed and
the former O2 is an orphaned diagnostic, not a clean successor. O1
overnight/intraday/decomposition is already outcome-tested and closed; it is
not reintroduced or rescued here.

## Frozen contract

### Control

`CONTROL_CLEAN_V2_COMMON_SUPPORT` uses the exact 25-feature
`HGB_XS_MARKET` order from the accepted V2 lineage:

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
11. `market_primary_liquid_count`
12. `market_breadth_return_5_positive`
13. `market_breadth_return_20_positive`
14. `market_median_close_return_5`
15. `market_median_close_return_20`
16. `market_median_atr14_over_close`
17. `market_median_close_position_20`
18. `market_median_relative_volume_20`
19. `market_median_log_regular_value_relative_20`
20. `market_relative_close_return_5`
21. `market_relative_close_return_20`
22. `market_relative_atr14_over_close`
23. `market_relative_close_position_20`
24. `market_relative_relative_volume_20`
25. `market_relative_log_regular_value_relative_20`

Feature-order SHA-256: `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72`.

The recorded model semantics are the accepted HGB contract: median
`SimpleImputer` with missing indicators and `keep_empty_features=True`, then
`HistGradientBoostingClassifier(learning_rate=0.05, max_iter=200,
max_leaf_nodes=31, l2_regularization=1.0, random_state=42)`. No model is
instantiated or fitted by this phase.

Frozen six-fold identity: V2F1 `(1–504, purge 505–524, validation 525–624)`;
V2F2 `(1–624, 625–644, 645–744)`; V2F3 `(1–744, 745–764, 765–864)`;
V2F4 `(1–864, 865–884, 885–984)`; V2F5 `(1–984, 985–1004, 1005–1104)`;
V2F6 `(1–1104, 1105–1124, 1125–1224)`. H10 semantics, evaluator, and the
eventual paired rule remain inherited unless a genuine contract incompatibility
is found; no post-outcome rescue is allowed.

### V2.1 — exact same-day Open geometry

Working identity: `V2.1-CLEAN-V2-OPEN-GEOMETRY`.

Append exactly, in this order:

1. `open_position = (Open_t - Low_t) / (High_t - Low_t)`;
2. `open_to_high = High_t / Open_t - 1`;
3. `open_to_low = Low_t / Open_t - 1`.

If the range is flat (`High_t <= Low_t`) or any required input is non-finite,
non-positive, or outside a valid Open range, all same-day geometry is missing
and the row is not in common support. No arbitrary fill or rescue is permitted.

### V2.2 — previous-range opening displacement

Working identity: `V2.2-CLEAN-V2-PREV-RANGE-OPEN-DISPLACEMENT`.

Append exactly, in this order:

1. `open_position_prev_active_range = (Open_t - Low_prev) / (High_prev - Low_prev)`;
2. `open_to_prev_high = High_prev / Open_t - 1`;
3. `open_to_prev_low = Low_prev / Open_t - 1`.

`prev` is the immediately preceding observed PIT-valid ACTIVE bar for the same
ticker, selected by official session index. It is not a calendar-day shift and
does not forward-fill through suspension/no-trade. A missing previous bar,
invalid/flat previous range, or invalid current Open is missing/fail-closed.
Previous session index and session gap are diagnostics only, not model features.

## Outcome-blind population freeze

The clean V2 source has 292,631 rows / 737 tickers, date range
2021-06-02–2026-07-17, session range 20–1250, zero duplicate identity keys,
and key SHA-256:

`79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826`.

One population is used for control and both challengers. The measured common
support is **277,244 rows / 729 tickers**, date range 2021-06-02–2026-07-17,
session range 20–1250, key SHA-256:

`e058e5ce4ce650eeab5acd57a7d697c155548e40bbbb8ffe0eab120987d857df`.

The three executable feature identities are separate and pinned:

| identity | feature count | feature-order SHA-256 |
|---|---:|---|
| CONTROL clean V2 | 25 | `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72` |
| V2.1 same-day geometry | 28 | `9bf62fd9fec1edeaebd7b3024512f942fcef9c7d12dd01797f2c2020bf636c34` |
| V2.2 previous-range displacement | 28 | `228c3afad2d4f786923c480e9b91be0467a646b08e770097552c8905dd30ff74` |

The 31-feature V2 + all-six-Open concatenation is a diagnostics-only column
order and is explicitly **PROHIBITED** as a fitted candidate.

Clean-V2 exclusions: **15,387** rows:

| reason | rows |
|---|---:|
| current Open unavailable/invalid | 12,589 |
| current flat range | 1,876 |
| previous ACTIVE flat/invalid range | 922 |

The 1,876 flat-range rows are also a provenance finding: the upstream
coverage CSV stores `open_position` as missing but stores `open_to_high` and
`open_to_low` as zero. The new contract treats the entire family as missing;
the external source was not modified.

## Frozen survivor and winner rule

For each challenger versus its comparator, the exact paired gate is:

- median paired PR-AUC delta > 0;
- q25 paired PR-AUC delta > 0;
- positive paired folds >= 2;
- fail the guardrail only when the candidate median ROC-AUC **and** median
  Q5-Q1 are both below the comparator.

Apply this gate separately to V2.1-vs-CONTROL and V2.2-vs-CONTROL. If neither
survives, the verdict is `RETAIN_CLEAN_V2`; if exactly one survives, that
challenger is the unique historical-development winner. If both survive, run
the same gate head-to-head in both directions on the already-produced
same-fold predictions. Exactly one directional pass selects that challenger;
otherwise the verdict is
`MULTIPLE_SURVIVORS_NO_UNIQUE_CHAMPION`. No post-hoc aggregate metric, era,
feature importance, or subjective preference may select a winner.

## Required no-rescue selection discipline

The eventual historical run may contain only the clean V2 control, V2.1, and
V2.2 above, on this exact common-support population, with the frozen folds,
labels, HGB settings, evaluator, and paired rule. No additional feature,
interaction, rolling variant, market-relative gap, hyperparameter search,
V2.3, or post-outcome subset selection is authorized.

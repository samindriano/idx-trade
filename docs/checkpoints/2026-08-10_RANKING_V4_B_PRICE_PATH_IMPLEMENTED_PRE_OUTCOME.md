# Ranking V4-B Price-Path Quality — Implemented Pre-Outcome

Date: 2026-08-10 (Asia/Jakarta)
Status: **IMPLEMENTATION PASS / LOCAL OUTCOME-BLIND CACHE AUDIT NEXT / OUTCOME RUN NOT AUTHORIZED**

## Decision state

Family `V4-B-PRICE-PATH-V1` is specified, reviewed and implemented through the pre-outcome tooling stage.

Reserved first-pass candidates:

- ordinal `015`: `V4-B-PRICE-PATH-V1-CONTROL-015` — exact final V3-B 33-feature HGB control;
- ordinal `016`: `V4-B-PRICE-PATH-V1-COHERENCE-016` — exact V3-B plus B1 Path Coherence / Jump Concentration;
- ordinal `017`: `V4-B-PRICE-PATH-V1-RANGE-ACCEPTANCE-017` — exact V3-B plus B2 Range Acceptance / Rejection.

No B1+B2 integration candidate exists. One integration may be designed later only if both challengers independently PASS under a separate authorization.

No V4-B candidate outcome has been viewed. V4 evaluated-candidate count remains `3`; cumulative historical evaluated count remains `12`.

## Frozen controlling design

Experiment map:

`docs/RANKING_V4_B_PRICE_PATH_EXPERIMENT_MAP_V1.md`

Exact spec:

`docs/RANKING_V4_B_PRICE_PATH_SPEC_V1.md`

Frozen spec Git blob:

`a750c28831b95b1c88640c5879289da5f2c05446`

Review addendum:

`docs/RANKING_V4_B_PRICE_PATH_SPEC_REVIEW_ADDENDUM_V1.md`

Ledger:

`docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`

## Frozen appended features

### B1 — ordinal 016

1. `v4b_path_efficiency_5`;
2. `v4b_path_efficiency_20`;
3. `v4b_largest_move_share_20`.

B1 measures gross-path efficiency and one-session movement concentration. It does not add alternate return magnitude, skew/kurtosis, trend-R2 or multiple lookback variants.

### B2 — ordinal 017

1. `v4b_range_acceptance_mean_5`;
2. `v4b_range_acceptance_mean_20`;
3. `v4b_extreme_close_balance_5`.

B2 measures repeated daily close acceptance/rejection inside each session's own high-low range. It is mechanically distinct from V3-B's aggregate 20-session `close_position_20` and Structure-Lite geometry.

## Implemented code

Feature construction:

`src/idx_trade/research_v4_price_path.py`

Candidate/model contract:

`src/idx_trade/ranking_v4_price_path.py`

Outcome-independent cache preparation:

`src/idx_trade/ranking_v4_price_path_prepare.py`

- exact frozen panel/calendar/V3-B cache identities are pinned;
- panel physical read is column-projected to `ticker/date/high/low/close`;
- exact V3-B rows/columns are preserved;
- session `1225+` is prohibited;
- manifest explicitly records no outcome/fresh-forward/integration materialization.

Outcome-blind audit:

`src/idx_trade/ranking_v4_price_path_audit.py`

- physically loads identity + exact V3-B 33 features + six V4-B features only;
- never loads `binary_target` or other outcome columns;
- reports coverage/distributions and every Spearman correlation involving V4-B;
- flags absolute Spearman `>=0.95`, constants and finite coverage below 80%.

Atomic first-pass runner:

`src/idx_trade/ranking_v4_price_path_run.py`

Implemented but **not authorized for execution**. When separately authorized after blind-audit review, it will run exact control+B1+B2 in one invocation, require frozen V3-B equivalence at `1e-12`, apply the unchanged V4-A challenger gate, emit top-decile overlap diagnostics and stop without integration.

CLI:

`src/idx_trade/ranking_v4_price_path_cli.py`

Local pre-outcome handoff:

`coordination/handoffs/IDX-RANKING-V4-B-PRICE-PATH-CACHE-AUDIT.md`

## Runtime-note compliance

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` was read before implementation.

Relevant implementation choices:

- no uncontrolled candidate/fold parallelism;
- same deterministic HGB semantics;
- column-projected raw-panel read for B1/B2 feature preparation;
- column-projected outcome-blind audit;
- exact control-equivalence requirement before any later challenger interpretation.

No performance change modifies model semantics.

## Tests / CI

V4-B implementation + focused tests were validated by GitHub Actions after implementation commit:

`1d409c7f88faa2069d0a7ffc4d2402c9cce76c8a`

Full repository pytest:

- `348 passed`;
- `0 failed`;
- `2062 warnings` in the CI environment (existing/deprecation-warning volume);
- pytest duration `12.25s`.

Focused V4-B tests cover:

- exact V3-B feature prefix and feature counts;
- frozen HGB parameters;
- monotonic-path efficiency;
- flat-path zero semantics;
- daily-range acceptance and extreme-close balance;
- official-session gap fail-closed behavior;
- zero-range close-location missingness;
- future-row causal invariance;
- label/outcome-column rejection;
- session-1225 boundary;
- first-pass integration prohibition;
- unchanged V4-A-style gate thresholds.

## Next permitted action

Execute only:

`coordination/handoffs/IDX-RANKING-V4-B-PRICE-PATH-CACHE-AUDIT.md`

The Windows-local task must stop after cache preparation + outcome-blind audit and return the report for ChatGPT review.

A separate ChatGPT checkpoint is required before any V4-B control/B1/B2 model is fitted or scored.

## Hard boundary confirmation

At this checkpoint:

- ordinal 015 result: `UNVIEWED`;
- ordinal 016 B1 result: `UNVIEWED`;
- ordinal 017 B2 result: `UNVIEWED`;
- B1+B2 integration: not materialized;
- sessions `1225+`: not materialized/scored by V4-B;
- post-2026-07-31 fresh-forward outcomes: not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED`: not written;
- V3-B remains immutable;
- V4-A remains closed without rescue;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge remain unauthorized.
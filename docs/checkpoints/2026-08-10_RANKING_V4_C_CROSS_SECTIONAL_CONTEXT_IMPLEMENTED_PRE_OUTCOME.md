# Ranking V4-C Cross-Sectional Opportunity Context — Implemented Pre-Outcome

Date: 2026-08-10 (Asia/Jakarta)
Status: **IMPLEMENTATION PASS / LOCAL OUTCOME-BLIND CACHE AUDIT NEXT / OUTCOME RUN NOT AUTHORIZED**

## Decision state

Family `V4-C-CROSS-SECTIONAL-CONTEXT-V1` is frozen, independently reviewed and implemented through pre-outcome tooling while V4-B remains pre-outcome.

This ordering is intentional: V4-C was specified without seeing any V4-B model outcome and therefore may not be adapted to later V4-B results.

Reserved first-pass candidates:

- ordinal `018`: `V4-C-CROSS-SECTIONAL-CONTEXT-V1-CONTROL-018` — exact final V3-B 33-feature HGB control;
- ordinal `019`: `V4-C-CROSS-SECTIONAL-CONTEXT-V1-DISPERSION-019` — exact V3-B plus one frozen four-feature cross-sectional dispersion bundle.

There is only one challenger. No second V4-C variant and no within-family integration candidate exists.

No V4-C outcome has been viewed. Cumulative historical evaluated-candidate count remains `12` until separately authorized future V4-B/V4-C outcome runs occur.

## Frozen design

Experiment map:

`docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_EXPERIMENT_MAP_V1.md`

Exact spec:

`docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md`

Frozen spec Git blob:

`43f222f31c7c0ea15e870d22b066aae95858c81f`

Review addendum:

`docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_REVIEW_ADDENDUM_V1.md`

## Frozen appended features

Ordinal `019` appends exactly:

1. `v4c_market_return_iqr_5`;
2. `v4c_market_return_iqr_20`;
3. `v4c_market_atr_iqr`;
4. `v4c_market_close_position_iqr_20`.

Each is a date-level IQR computed from the **full causal primary-liquid universe** using exact existing V2 baseline-feature semantics. Minimum finite cross-section is 50. Quantiles use explicit linear interpolation. No log transform, winsorization, regime threshold, alternate quantile band or volume/value dispersion variant exists.

The family deliberately excludes participation dispersion so V4-C does not become a backdoor rescue of closed V4-A.

## Implemented code

Feature/context construction:

`src/idx_trade/research_v4_cross_sectional_context.py`

- reconstructs exact causal V2 baseline features from the bounded signal panel;
- uses full `universe_primary_liquid` rows per date before outcome/model-row filtering;
- computes one four-feature context row per date;
- rejects label/outcome columns;
- enforces session boundary and causal future-row invariance.

Candidate/model contract:

`src/idx_trade/ranking_v4_cross_sectional_context.py`

- exact 33-feature V3-B prefix;
- exact frozen V3-B HGB parameters;
- ordinal 018 control + ordinal 019 challenger only;
- no integration candidate;
- frozen spec blob pinned.

Outcome-independent cache preparation:

`src/idx_trade/ranking_v4_cross_sectional_context_prepare.py`

- pins exact panel/calendar/V3-B cache identities;
- physically projects raw panel to `ticker/date/high/low/close/volume/regular_market_value`;
- constructs context from full primary-liquid universe;
- joins date-level context to exact V3-B rows without changing existing columns/order;
- records context-date and primary-liquid cross-section diagnostics;
- prohibits session `1225+` and fresh-forward materialization.

Outcome-blind audit:

`src/idx_trade/ranking_v4_cross_sectional_context_audit.py`

- physically loads identity + exact V3-B 33 features + four V4-C features only;
- never loads `binary_target` or other outcome columns;
- verifies V3-B/V4-C date-level context is constant within signal date;
- reports row-level Spearman against all 33 V3-B features;
- reports separate date-level Spearman against existing V3-B market-context features;
- mechanical review threshold is absolute **date-level** Spearman `>=0.95`, constant feature, or finite rate below 80%.

Atomic first-pass runner:

`src/idx_trade/ranking_v4_cross_sectional_context_run.py`

Implemented but **not authorized for execution**. A later separately authorized run will:

1. load exact frozen V3-B F1-F4/F5-F6 references;
2. score exact ordinal 018 control;
3. require exact score/metric equivalence at `1e-12`;
4. score ordinal 019 in the same invocation with no adaptation;
5. apply the exact unchanged V4-A/V4-B challenger gate;
6. emit top-decile overlap diagnostics;
7. stop with PASS/FAIL and no rescue.

CLI:

`src/idx_trade/ranking_v4_cross_sectional_context_cli.py`

Local pre-outcome handoff:

`coordination/handoffs/IDX-RANKING-V4-C-CROSS-SECTIONAL-CONTEXT-CACHE-AUDIT.md`

## Runtime-note compliance

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` was controlling during implementation.

Relevant choices:

- one context reconstruction pass;
- column-projected Parquet input;
- no uncontrolled candidate/fold parallelism;
- no reuse of training-dependent preprocessing;
- exact control-equivalence requirement for any later scoring;
- no performance optimization that changes V2 baseline semantics.

## Tests / CI

All V4-C code through focused-test commit:

`70818d509903749b9656ed994afda9976955c0a3`

was validated by GitHub Actions:

- `357 passed`;
- `0 failed`;
- `2062 warnings` in CI, dominated by existing/deprecation-warning volume;
- pytest duration `16.85s`.

Focused V4-C tests cover:

- frozen linear-IQR semantics and 50-stock minimum;
- full primary-liquid cross-section construction;
- below-minimum missingness;
- future-row causal invariance;
- outcome-column rejection;
- exact V3-B feature prefix and exact HGB parameters;
- control+one-challenger candidate set only;
- session-1225 hard block;
- semantic identity of the V4-C gate with the frozen V4-A gate.

## Next permitted action

V4-B and V4-C may have their **outcome-blind cache/audit tasks** prepared independently because neither requires or may consume the other's outcomes.

For V4-C execute only:

`coordination/handoffs/IDX-RANKING-V4-C-CROSS-SECTIONAL-CONTEXT-CACHE-AUDIT.md`

A separate ChatGPT review/checkpoint is required before ordinal `018/019` may be fitted/scored.

## Hard boundary confirmation

At this checkpoint:

- ordinal 018 result: `UNVIEWED`;
- ordinal 019 result: `UNVIEWED`;
- V4-C outcome metrics: not computed;
- session `1225+`: not materialized/scored by V4-C;
- post-2026-07-31 fresh-forward outcomes: not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED`: not written;
- V3-B remains immutable;
- V4-A remains closed without rescue;
- V4-B outcome remains irrelevant to frozen V4-C definition;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge remain unauthorized.
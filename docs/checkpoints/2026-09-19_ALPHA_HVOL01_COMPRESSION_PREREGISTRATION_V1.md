# H-VOL-01 Volatility Compression — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `E_G_OUTCOME_BLIND_STRUCTURAL_DIAGNOSTIC`  
Status: `PREREGISTERED / NO CANDIDATE ID`

## Question

Does a fixed daily range-compression state provide a structurally distinct,
well-supported, implementable research direction from C1/C2/C4 and H-LIQ-01?

This is a mechanism diagnostic only. It does not assert that compression
predicts returns, and it cannot create C5 without a later novelty and
admission decision.

## Fixed representation

For each ticker and official session `t`, using only the observed EOD `high`,
`low`, and `close` at or before `t`:

1. `range_pct_t = (high_t - low_t) / close_t` when all values are positive,
   finite, and `high_t >= low_t`; otherwise missing.
2. `short_range_t = median(range_pct, 5 official sessions)`.
3. `long_range_t = median(range_pct, 60 official sessions)`.
4. `H-VOL-01_t = -log(short_range_t / long_range_t)` when both medians are
   positive and finite. Higher values mean greater recent compression relative
   to the fixed 60-session state.

There is exactly one representation: 5/60 sessions, median aggregation, and
the compression direction above. No lookback sweep, sign flip, threshold
search, winsorization, sector residualization, or outcome-conditioned choice is
allowed in this diagnostic.

## Structural tests declared before execution

- finite eligible row/date/ticker support;
- score distribution and numerical validity;
- Top-30 turnover distribution and persistence;
- Top-30 overlap and daily rank dependence versus C1/C2/C4;
- selected market-value quartile composition;
- source/session/anchor/manifest/code/repository hash binding;
- explicit target/provider/outcome access flags.

No target, forward return, label, incumbent target-derived score, IC, ICIR,
OOS metric, or predictive proxy may be read or computed.

## Decision rules

- `PASS_STRUCTURAL_ONLY`: construction and declared diagnostics complete.
- `FUTURE_RESEARCH`: structurally credible but novelty/economics/PIT remain
  unresolved.
- `NOVELTY_PENDING`: overlap or shared exposure is too material to admit a
  candidate ID, but the mechanism is not structurally rejected.
- `STRUCTURALLY_REJECTED`: invalid, unsupported, or redundant under the fixed
  diagnostic.

No result can become `READY_FOR_REENTRY`, `RESEARCH_SURVIVOR`, or a production
model from this experiment.

## Integrity-completion addendum — 2026-09-19

The first deterministic run produced the fixed formula/support/turnover/Top-30
overlap fields but omitted two diagnostics already declared above: score
distribution/numerical checks and daily rank dependence. Independent review
also identified the useful bounded comparison to H-LIQ-01 and turnover-quartile
composition. A rerun is therefore authorized solely to complete the declared
artifact contract and add those target-free diagnostics; the formula, inputs,
windows, direction, and candidate budget are unchanged. This is not a
parameter retry, sign rescue, or outcome-driven selection.

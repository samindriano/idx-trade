# Ranking V4-A Review Closed / V4-B Specification Authorized

Date: 2026-08-10 (Asia/Jakarta)
Status: **V4-A CLOSED / V4-B SPECIFICATION AUTHORIZED ONLY**

## Review decision

`V4_A_PARTICIPATION_CLOSE_NO_SURVIVOR`

The single authorized atomic V4-A first-pass run is accepted as the final historical-development result for Family V4-A.

- ordinal `012` exact V3-B control: control equivalence PASS;
- ordinal `013` A1 Impact/Absorption: FAIL;
- ordinal `014` A2 Persistent Directional Participation: FAIL;
- survivors: none;
- A1+A2 integration: not authorized and must not be created;
- no rescue, reformulation, threshold change, lookback change, feature ablation chosen from outcome, or second participation candidate is allowed.

The family is closed. The V4-A result does not alter the frozen V3-B benchmark.

## Interpretation

A1 changed rankings materially but did not deliver robust incremental value. Its paired PR result was weak overall and deteriorated sharply in V2F6, while Q5-Q1 changes were nonnegative on only one of six folds.

A2 was closer on PR than A1 and its V2F5/V2F6 paired PR changes were both positive. That is not sufficient for promotion: A2 still failed the frozen broad-robustness gate, including only four of six nonnegative PR folds, negative q25/worst PR behavior, median ROC deterioration beyond tolerance, and broad Q5-Q1 degradation. The late-fold behavior may be recorded descriptively but may not be harvested into a rescue hypothesis.

The defensible conclusion is therefore limited to:

> The tested daily-EOD Participation Quality / Price-Impact definitions did not add sufficiently robust incremental cross-sectional ranking alpha beyond frozen V3-B.

This does not establish that all possible liquidity or order-flow information lacks alpha; it closes only the already-frozen V4-A daily-EOD family implementation.

## Next family

The next permitted V4 lane is:

**V4-B — Price-Path Quality — SPECIFICATION FIRST.**

Research question:

> Conditional on the frozen V3-B state and geometry information, does the *way* the current setup was formed — coherent versus jump-concentrated movement, and acceptance versus rejection within daily ranges — add robust cross-sectional ranking information?

The specification phase should reduce the broad Price-Path family into at most two genuinely distinct pre-outcome sub-hypotheses. The preferred conceptual split is:

1. **Path Coherence / Jump Concentration** — whether a 20-session move is persistent and distributed through the path versus dominated by one/few extreme sessions or noisy reversals;
2. **Range Acceptance / Rejection Quality** — whether recent sessions consistently close favorably within their own high-low ranges versus show repeated rejection/excursion behavior.

Tail asymmetry, trend coherence, spike concentration, candle/range quality and similar ideas must be merged into these questions rather than scored as many variants. No third sub-hypothesis should be added without a clear pre-outcome orthogonality justification.

## V4-B specification constraints

Before any implementation or outcome scoring:

- inspect the exact frozen V3-B 33-feature set and document overlap;
- use only causal after-close information available in the existing signal panel unless a separate data gate is passed;
- historical Open remains unnecessary unless independently justified and provenance-safe;
- keep exact V3-B target/model/folds as common benchmark unless the specification explicitly proves otherwise;
- freeze exact formulas, windows, feature order, missingness semantics, candidate ordinals and gates before outcomes;
- prefer compact bundles and no model/hyperparameter tournament;
- if two V4-B sub-hypotheses are retained, fully specify both before either result is viewed and score them atomically/parallel-equivalently;
- no V4-B outcome scoring is authorized by this checkpoint.

## Outcome boundary

At this checkpoint:

- cumulative historical evaluated-candidate count remains `12`;
- sessions `1225+` remain sealed from V4 development;
- post-2026-07-31 fresh-forward outcomes remain unaccessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge remain unauthorized.

## Next action

ChatGPT may now design and review a V4-B Price-Path specification. Do not fit or score V4-B until a separate frozen-spec implementation/outcome authorization exists.

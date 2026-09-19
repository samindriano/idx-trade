# H-LIQ-01 Source-Decomposition Diagnostic — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `D/E/F/G/J/K — TARGET-FREE STRUCTURAL DIAGNOSTIC`  
Hypothesis: `H-LIQ-01`

## Question

Does H-LIQ-01 retain a distinct target-free cross-sectional component after
removing the turnover-level information already represented in C2?

This is an orthogonality/novelty diagnostic, not a new candidate. It may not
create C5, access outcomes, tune on returns, or change the protected packet.

## Frozen construction

1. Build the same eligible decision universe and 600-session surface used by
   the retained H-LIQ diagnostic.
2. Compute baseline H-LIQ-01 exactly as the rolling 20-session standard
   deviation of `log(close * volume)`.
3. Compute the fixed C2 turnover-level component exactly as
   `log(mean(turnover, 5) / median(turnover, 60))`.
4. On each date, among rows with finite eligible baseline and level values,
   convert both values to percentile ranks using average ties.
5. Fit one cross-sectional OLS with intercept:
   `rank(H-LIQ-01) = intercept + beta * rank(C2 turnover-level)`.
   The diagnostic score is the residual. No other predictors, weights,
   transformations, horizons, or thresholds are allowed.

## Predeclared measurements

- finite residual rows and dates;
- daily Spearman of baseline/residual versus turnover-level, C2, C1, and C4;
- baseline/residual Top-30 common dates, overlap, and turnover distribution;
- baseline/residual selected bottom-value Q1 share;
- exact source/code hashes and access flags.

## Interpretation boundary

A residual that remains supported and compositionally distinct is evidence that
H-LIQ contains information not explained by this one C2 component. It is not
proof of economic novelty or predictive value. A residual that collapses,
loses support, or becomes a monotonic restatement of existing candidates is
evidence against upgrading novelty. In either case, H-LIQ remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION` unless a separate
decision explicitly freezes a new contract; no C5 is created by this run.

## Boundary and output

Inputs are the already staged panel, guarded features, official sessions, and
tradability anchors. Output must remain under the isolated
`idx-alpha-available-data-staging-20260919` root. No provider, network,
canonical, production, capture, cloud/R2, target, outcome, or telemetry state
may be read or modified.

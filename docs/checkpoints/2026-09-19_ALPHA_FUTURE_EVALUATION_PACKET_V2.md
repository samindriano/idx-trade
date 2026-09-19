# Alpha Future Evaluation Packet V2

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `SPECIFICATION_ONLY / BLOCKED_BY_DATA_ADMISSION`  
Contract: `research/alpha_future_evaluation_packet_v2_contract.json`

This V2 is a static contract-closure revision of V1. It does not open targets,
change the protected candidate budget, refit a model, or authorize evaluation.
V1 remains preserved for lineage; this document is the current re-entry
specification candidate.

## 1. Protected candidate budget and execution gates

The protected budget remains exactly C1–C4:

| ID | Candidate | Current execution gate |
|---|---|---|
| C1 | `residual_reversal_5_v1` | `ADMISSION_REQUIRED` |
| C2 | `participation_confirmation_5_v1` | `ADMISSION_REQUIRED` |
| C3 | `financial_quality_growth_v1` | `BLOCKED_C3_PIT_COVERAGE`; `execute=false` |
| C4 | `path_efficiency_reversal_20_v1` | `ADMISSION_REQUIRED` |

C3 is deliberately retained as a registered hypothesis but cannot execute if
the global admission gate passes. It requires a separate fresh financial
population/PIT/vintage admission and an explicit status decision before any
protected read. C1/C2/C4 also remain blocked until the global admission
artifact passes. No H-LIQ, H-VOL, H-EXC, combination, or new candidate ID is
added.

## 2. Direct source and implementation bindings

The machine-readable contract binds the exact paths and SHA-256 values for:

- frozen panel;
- financial bundle;
- official sessions;
- tradability anchors;
- guarded Stage-A feature artifact;
- Stage-A manifest;
- corrected Stage-A code;
- protocol;
- required structural/PIT/CA/capacity evidence.

The binding contract is self-contained at
`research/alpha_future_evaluation_packet_v2_contract.json`. A verifier must
hash every explicit path and fail closed on any missing, changed, or
conflicting value. It must also verify the panel/feature key digest and exact
row count before any future protected read.

## 3. Frozen candidate formula and feature-missingness contract

- C1 requires finite fixed beta-60-through-`t-1`, volatility-20, and
  residual-5 observations. No shorter fallback or imputation is permitted.
- C2 requires finite prior-5 return and finite 5-session mean / prior-60
  median turnover. Invalid or zero `close*volume` is missing, not imputed.
- C3 requires all five values, same-bundle provenance, reporting version and
  attachment hash, valid knowledge-time ordering, valid period boundary, and
  eligible-universe membership. Partial bundles and fallback values are
  forbidden; current execution is explicitly disabled.
- C4 requires finite prior-20 returns and a strictly positive finite sum of
  absolute prior daily returns. Zero denominator and shorter fallback are
  missing.
- Every candidate score is finite only when its entire fixed formula contract
  is satisfied. A missing score is excluded from that date's candidate support;
  it is never zero-filled.
- Rolling operations use `min_periods=window`; official-session ordering is
  mandatory; no future row, survivorship repair, or candidate-specific
  population is allowed.

## 4. Ranking and deterministic tie contract

The eligibility mask is applied before aggregation, scoring, and ranking.
Candidate ranks use `method="average", pct=True`. Score direction is the
frozen formula direction; no sign flip or post-access normalization is
allowed. Top-K selection is deterministic: score descending, ticker ascending,
stable mergesort, with `K=30`. Same-date candidate and incumbent rows must
share the exact eligible support.

## 5. Population, targets, folds, and purge

- Population: `V4_PRIMARY_LIQUID_CAUSAL_V1`, requiring PIT common-share,
  `LISTED`, `ACTIVE`, and the frozen trailing-60 official-session
  regular-market-value rule: at least 20 finite observations and median at
  least IDR 1 billion.
- `ELIGIBILITY_CONTRACT_STATUS: BLOCKED_POLICY_CONFLICT`. The prose minimum-20
  rule conflicts with the implementation's `min_periods=window` behavior.
  The current implementation population is 310,761 rows, while the literal
  minimum-20 interpretation is 348,765 rows; the 38,004-row difference is not
  a permitted population choice. This packet is not executable until an
  authoritative contract resolution is recorded and re-hashed.
- Security/issuer/ISIN continuity, corporate-action transition basis,
  revision/vintage, and population completeness must be independently
  admitted; the current mask alone is not authority for those properties.
- Target: `CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1`.
  H5/H10 are `Close_(t+h) / Open_(t+1) - 1`, with missing horizons missing,
  never zero-filled; consensus is the predeclared equal-weight average of
  ascending average-tie ranks.
- Six chronological non-overlapping 100-session folds over the frozen
  historical design window; ten official-session purge before each validation
  start; preserve the predeclared observability rules.
- No substitute target, H5-only run, proxy label, target reconstruction,
  rescue, refit, sign flip, variant sweep, or boundary shift.

## 6. Predeclared metrics and gates

Metrics remain those in V1: daily cross-sectional Spearman IC, six-fold median
and q25 IC, ICIR, positive-session/fold fraction, Top-30 target percentile,
Top-30 minus Bottom-30 spread, H5/H10 separately, and the fixed 2,000-repetition
block bootstrap (block length 10, seed 42). No metric may be added after
outcomes are visible.

The fixed survivor gates remain: median fold IC `>=0.025`, q25 `>=0.010`, at
least five positive folds, Top-30 percentile `>=0.52`, spread `>=0.04`,
bootstrap lower bound `>0`, paired mean IC delta `>=0.005`, paired spread delta
`>=0.010`, paired Top-30 delta `>=0.005`, paired q25 delta `>=0`, at least four
positive fold deltas, and both H5/H10 present. Any failed/unknown gate stops
the run and leaves the queue unchanged.

## 7. Frozen economics and robustness evidence

- Buy fee 15 bps, sell fee 25 bps, slippage 10 bps per side; sensitivity
  0/25 bps per side; 15% EOD NAV entry cap.
- The 1% regular-market-value number is a causal proxy only, not ADV, spread,
  queue, fill probability, or broker capacity. The stamp-duty rule must be
  resolved before admission; unresolved means blocked.
- Required structural evidence is hash-bound in the contract: robustness,
  CA/price-basis, capacity, C3 contract, H-LIQ decomposition, and Phase-Q
  correction artifacts. This is an evidence checklist, not a second PASS route
  or permission to tune after target access.

## 8. Admission gate and stopping rule

Before any protected read, a fresh independent artifact must prove population
completeness, PIT/as-of authority, common-share and issuer/ISIN continuity,
calendar continuity, corporate-action transition basis, revision/vintage
completeness, H5/H10 authority, immutable incumbent/common-support identity,
and untouched protected-evaluation/counter/lock state. Any missing or UNKNOWN
item is a fail-closed `BLOCKED` result.

At most one execution is allowed per candidate after all gates pass. C3 cannot
execute under this contract while its candidate gate is `BLOCKED_C3_PIT_COVERAGE`.
No production promotion follows historical evaluation; prospective untouched
evidence remains separately required.

## Current verdict

`NO-GO FOR RE-ENTRY / BLOCKED_BY_DATA_ADMISSION`

The V2 contract is more explicit and machine-verifiable, but it does not
weaken the scientific boundary or manufacture an admission artifact. The
current next step is to re-run the independent packet verifier on this V2
contract. Only an independent Data QA admission can move beyond this point.

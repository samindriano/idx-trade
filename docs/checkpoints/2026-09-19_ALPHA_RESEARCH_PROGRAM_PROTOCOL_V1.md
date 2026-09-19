# Alpha Research Program — Frozen Protocol V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Base: `37a82293c2ff0c91a5fc3c8068536d91bf06f10f`
Status: `FROZEN_BEFORE_NEW_OUTCOME_ACCESS`

## Purpose and boundary

This is an isolated historical-research lane for testing a small, predeclared
portfolio of genuinely distinct alpha mechanisms against the frozen V4-X1
incumbent. It does not modify or write to the incumbent, V4-X1, Decision V2,
canonical data, capture/runtime, cloud/R2, scheduler, counters, or protected
prospective data.

All materialized features, scores, metrics, manifests, and derived data must
remain in this lane's staging area or in explicitly named research artifacts.
No prompt, credential, user content, or unnecessary personal data may be
stored. No provider probe is part of this protocol.

This protocol is frozen before opening any historical target/forward-label
artifact for the new candidates. Stage A is outcome-blind. Historical target
access, if needed, is limited to the fixed non-prospective six-fold protocol
below and cannot be represented as prospective validation.

## Frozen incumbent and target

- Incumbent: `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`.
- Incumbent fingerprint: `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`.
- Ranking: `alpha_consensus DESC, ticker ASC`.
- Target: `CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1`.
- H5: `Close_(t+5) / Open_(t+1) - 1`.
- H10: `Close_(t+10) / Open_(t+1) - 1`.
- Within-session target ranks are ascending average-tie ranks; consensus is
  `0.5 * H5_rank + 0.5 * H10_rank`. Missing horizons are not zero.

The authoritative universe is `V4_PRIMARY_LIQUID_CAUSAL_V1`: PIT common
shares that are `LISTED` and `ACTIVE` at EOD `t`, with the frozen trailing-60
official-session median regular-market-value eligibility rule, at least 20
finite observations, and minimum median IDR 1 billion. No future-derived
universe or top-N substitute is allowed.

## Historical evaluation design

The only outcome-opening design admitted in this lane is the existing frozen
historical development/OOS design:

- six chronological, non-overlapping 100-session folds;
- the last 600 consensus-eligible sessions;
- ten official-session purge; validation start `s` excludes training signal
  sessions `s-10..s-1`;
- at least 90 admitted metric dates per fold;
- H5 and H10 are evaluated separately and the frozen consensus is the primary
  comparison;
- validation currently ends at session 1249 / 2026-07-17.

This is not a fresh prospective holdout. The current clean panel has only ten
post-cutoff sessions and cannot mature a new H5/H10 consensus holdout. A
H5-only substitution, a shifted cutoff, or a different target is prohibited.

## Metrics and fixed gates

Primary metric: daily cross-sectional Spearman IC on exactly the same eligible
rows and dates for incumbent and candidate. Secondary metrics are median and
q25 fold IC, ICIR, positive-session/fold fraction, Top-30 mean target
percentile, Top-30 minus Bottom-30 spread, and fold-stratified moving-block
bootstrap (2,000 repetitions, block length 10, seed 42).

For a candidate to be a historical `RESEARCH_SURVIVOR`, all of the following
must hold for the consensus comparison unless a stricter frozen contract is
encountered:

- candidate absolute gates: median fold IC >= 0.025, q25 fold IC >= 0.010,
  at least 5 positive folds, Top-30 percentile >= 0.52, spread >= 0.04, and
  bootstrap lower bound > 0;
- paired improvement over incumbent: consensus mean IC delta >= 0.005,
  spread delta >= 0.010, Top-30 delta >= 0.005, q25 delta >= 0, and at least
  4 positive fold deltas;
- both H5 and H10 remain present under their frozen target-observability
  rules. H5-only evidence cannot pass the consensus gate.

For the individual horizons, the existing stricter/appropriate frozen H5/H10
gates remain in force; no new threshold is invented after results are visible.
All economic figures use the frozen execution assumptions only as a later
research diagnostic: buy fee 15 bps, sell fee 25 bps, slippage 10 bps per
side, sensitivity 0/25 bps, the existing stamp-duty rule, 15% EOD NAV entry
cap, and 1% causal regular-market-value capacity reference. These figures are
not broker-fill or production claims.

## Stage A, orthogonality, and robustness gates

Before any target access, every candidate must pass structural checks:

- features use EOD `t` and strictly prior observations only;
- no centered window, future fill, target-conditioned selection, or
  post-outcome winsorisation/feature selection;
- unique `(ticker, date)` keys, finite feature values where eligible, and no
  outcome-like fields in feature artifacts;
- deterministic feature hash and complete provenance (source hash, schema,
  timestamp, code/commit identity);
- cross-sectional ranks are applied only after the authoritative same-session
  decision-universe mask is joined;
- coverage, missingness, and eligibility effects are reported by date and
  ticker, not hidden by aggregate averages;
- incumbent overlap/correlation, conditional incremental information,
  concentration, and regime/period slices are recorded before any verdict.

Fixed robustness views are: six fold results, first/last half of the frozen
historical window, calendar/regime slices already defined by the incumbent
contract, parameter perturbation only where explicitly listed below, ticker
and date breadth, and missingness/eligibility sensitivity. No alternate slice
may create a second PASS route.

## Bounded candidate roster

Exactly four first-pass candidates are admitted. Each is one fixed formula;
there are no sign, weight, threshold, horizon, model, or feature-subset
sweeps. A candidate that fails Stage A is recorded as `BLOCKED` or `FAIL` and
is not rescued with variants.

### C1 — market-relative short reversal

`residual_reversal_5_v1`: estimate each security's prior-only 60-session beta
to the same-session equal-weight market return using only observations ending
before `t`; form the prior 5-session return residual to that market return;
rank the negative residual divided by prior 20-session realized volatility.
The fixed hypothesis is that short-lived security-specific dislocation can
mean-revert after controlling for broad market movement. Minimum history is
the fixed 60/20/5 windows; no shorter fallback is allowed.

### C2 — participation confirmation

`participation_confirmation_5_v1`: compute prior-only 5-session security return
multiplied by the prior-only log abnormal turnover ratio, where turnover is
`close * volume` and abnormal turnover is the 5-session mean divided by the
prior 60-session median. The fixed hypothesis is that price movement confirmed
by unusual participation contains continuation information. Zero/invalid
turnover is missing, not imputed.

### C3 — PIT financial quality and growth

`financial_quality_growth_v1`: on rows with all five selected values available
and complete selected-bundle provenance, average equal-weight cross-sectional
ranks of `-leverage_liabilities_to_assets`, `liquidity_cash_to_assets`,
`margin_net_income_to_revenue`, `yoy_revenue`, and `yoy_total_assets`. The
financial row is admitted only at its selected knowledge time and same
decision date. The fixed hypothesis is that a simple PIT quality/growth
composite adds slower-moving information not represented by price-path shape.
No partial-bundle fallback is allowed.

### C4 — path efficiency

`path_efficiency_reversal_20_v1`: compute prior-only 20-session net return
divided by the sum of absolute prior daily returns, then rank the negative of
that efficiency score. The fixed hypothesis is that an unusually one-sided,
low-friction price path is more vulnerable to medium-horizon reversal. Zero
denominator is missing; no parameter rescue is allowed.

These are mechanism-level hypotheses, not a claim that any will win. C1/C4
may be rejected for overlap with the incumbent; C2 may be rejected for overlap
with the already-tested effort/participation family; C3 is not the same as the
previous exact financial-event candidate, but its result must still be kept
separate from that failure.

## Multiple-testing, stopping, and status

The candidate budget is four fixed formulas plus one incumbent control. Stage A
may use only outcome-blind structural diagnostics. After Stage A, at most one
historical evaluation per admitted candidate is allowed; no retry, rescue,
variant, or search-until-win loop is allowed.

The ledger must contain every candidate and every failure, including blocked
sources and candidates rejected for coverage, PIT, overlap, or economics.
The phase stops at the first fully gated historical `RESEARCH_SURVIVOR`, or
after all four candidates are evaluated/blocked. It also stops immediately on
an integrity or provenance gate failure.

`RESEARCH_SURVIVOR` is historical evidence only. Promotion remains
`BLOCKED / WAITING_FOR_PROSPECTIVE_EVIDENCE` until a later untouched canonical
H5/H10 prospective evaluation passes. No incumbent replacement or production
test follows automatically.

## Non-negotiable no-go conditions

Do not open protected prospective outcomes, forward labels, counters, or
Outcome Vault artifacts. Do not alter canonical or production files. Do not
reopen historically blocked Investing/TradingView/Open approximations as
evidence. Do not use PARTIAL/BLOCKED/UNKNOWN sources for scientific claims.

# Alpha Structural Robustness Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `F_K_I_J_OUTCOME_BLIND_ROBUSTNESS`  
Result: `PASS_STRUCTURAL_ONLY / NOT ALPHA EVIDENCE`

## Question and non-redundancy rationale

The earlier structural lab covered fixed Top-K mechanics, six time blocks,
market-state conditioning, liquidity exposure, and daily/rolling overlap. It
did not answer whether the fixed formulas are sensitive to reasonable horizon
perturbations, monotone score normalization, random score missingness, or
universe perturbation. This battery answers those distinct structural
questions. It does not access targets, forward returns, incumbent scores,
provider data, or protected outcomes.

Perturbed horizons are diagnostic representations only. They do not create C5+
IDs, change the four-candidate budget, or authorize future evaluation.

## Frozen inputs and method

- Baseline feature artifact: `alpha_stage_a_v3_features.parquet`.
- Clean frozen OHLCV panel, official 1,260-session calendar, and the frozen
  tradability-anchor artifact.
- Evaluation window: the last 600 official sessions, `2024-01-12` through
  `2026-07-31`.
- C1/C2 horizon diagnostics: `h3`, fixed `h5`, `h10`.
- C4 horizon diagnostics: `h10`, fixed `h20`, `h40`.
- Rank/normalization diagnostics: cross-sectional percentile rank, ordinary
  z-score, and robust z-score. These are monotone transforms of the same daily
  score and are not new information sources.
- Missingness stress: deterministic row masking at 0.5%, 1%, and 5%; this is a
  sensitivity test, not a claim about the source's missingness process.
- Universe stress: three deterministic 10%-ticker-removal samples per
  candidate. Top-30 overlap and percentile shift are the useful outputs;
  common-name order Spearman is expected to remain 1.0 because raw scores are
  unchanged for names retained in both universes.
- Temporal diagnostics: calendar-year coverage and rolling 120-session
  Top-30 turnover.

Before perturbation, each fixed recomputation matched the admitted feature
artifact exactly over the finite pairs:

| Candidate | Finite pairs | Max absolute difference | Result |
|---|---:|---:|---|
| C1 | 154,939 | 0.0 | `PASS` |
| C2 | 155,679 | 0.0 | `PASS` |
| C4 | 155,509 | 0.0 | `PASS` |

## Lookback sensitivity

Top-30 turnover and same-day Top-30 overlap against the fixed baseline are:

| Candidate / horizon | Mean turnover | Mean overlap vs fixed |
|---|---:|---:|
| C1 h3 | 50.21% | 12.11% |
| C1 h5 fixed | 42.15% | 100.00% by definition |
| C1 h10 | 29.84% | 12.04% |
| C2 h3 | 42.82% | 11.67% |
| C2 h5 fixed | 32.91% | 100.00% by definition |
| C2 h10 | 21.94% | 11.46% |
| C4 h10 | 30.77% | 11.29% |
| C4 h20 fixed | 23.70% | 100.00% by definition |
| C4 h40 | 15.99% | 12.08% |

Interpretation:

- Horizon is a real representation choice, not a cosmetic parameter. Every
  tested alternative has low same-day Top-30 overlap with its fixed parent.
- Shorter horizons increase churn; longer horizons reduce churn. That is an
  implementation trade-off, not evidence of predictive superiority.
- The fixed horizons remain the only registered contracts. Alternative
  horizons are future research questions and must not be silently substituted.

## Monotone normalization invariance

For every candidate, percentile rank, ordinary z-score, and robust z-score
matched the fixed Top-30 set on all 600 usable dates: exact set-match rate
`100%`, with identical turnover and Top-30 overlap.

This closes a narrow redundancy question: carrying these transforms as
separate candidates would duplicate the same daily ordering. It does not
establish that a raw-score model or any target-based combination would work.

## Missingness stress

At 5% deterministic score masking, all broad-coverage candidates retained 600
dates with at least 30 names and their mean Top-30 overlap versus baseline was:

| Candidate | Finite-row loss | Mean Top-30 overlap | Mean turnover |
|---|---:|---:|---:|
| C1 | 4.996% | 94.88% | 44.94% |
| C2 | 4.942% | 95.17% | 36.16% |
| C4 | 4.991% | 95.03% | 27.23% |

C3 is qualitatively different: its baseline has only 278 usable Top-30 dates;
under 0.5%, 1%, and 5% masking it has only 276, 277, and 273 usable Top-30
dates respectively, while hundreds of the 600 calendar dates remain below the
Top-30 support threshold. This is additional structural evidence for
`BLOCKED`, not a reason to impute or forward-fill financial values.

The stress is synthetic and independent of source missingness. It cannot prove
source robustness or PIT completeness.

## Universe perturbation

Removing approximately 10% of tickers produced the following mean Top-30
overlap ranges across three deterministic samples:

| Candidate | Top-30 overlap range | Mean common-name percentile shift range |
|---|---:|---:|
| C1 | 87.01%–88.95% | 0.00653–0.00730 |
| C2 | 89.11%–91.40% | 0.00569–0.00656 |
| C3 | 89.43%–94.92% | 0.00651–0.00879; sparse dates |
| C4 | 87.40%–91.16% | 0.00635–0.00732 |

The common-name order Spearman result is `1.0` by construction: removing names
does not change the score order of names that remain. It is recorded as an
invariant, not as independent evidence of predictive stability. Top-K overlap
and percentile shift are the meaningful universe-sensitivity diagnostics.

## Temporal robustness

Calendar-year finite coverage for the broad candidates was:

| Candidate | 2024 | 2025 | 2026 partial year |
|---|---:|---:|---:|
| C1 | 99.58% | 99.55% | 99.42% |
| C2 | 100.00% | 100.00% | 100.00% |
| C4 | 99.86% | 99.91% | 99.90% |

C3 coverage was `0%` in 2024, `22.63%` in 2025, and `39.41%` in the 2026
partial year. This is a capability/timing failure, not a return result.

Rolling 120-session Top-30 turnover was:

| Candidate | Mean | Std. dev. | Q10–Q90 |
|---|---:|---:|---:|
| C1 | 42.06% | 1.75 pp | 40.03%–44.48% |
| C2 | 32.52% | 1.43 pp | 30.94%–34.59% |
| C3 | 10.78% | 0.70 pp | 9.69%–11.61%; sparse only |
| C4 | 23.59% | 1.91 pp | 21.31%–26.48% |

## Structural disposition

| Candidate | Updated structural interpretation | Status change |
|---|---|---|
| C1 | Horizon-sensitive, high-churn, broad-coverage; 5% synthetic masking remains implementable | stays `FUTURE_RESEARCH` |
| C2 | Horizon-sensitive, moderate-churn, broad-coverage; most stable coverage and universe overlap of the broad candidates | stays `FUTURE_RESEARCH` |
| C3 | Normalization-invariant but support-fragile; even small missingness leaves many dates unusable | stays `BLOCKED` |
| C4 | Horizon-sensitive, lower-churn, broad-coverage; fixed representation remains distinct from horizon variants but overlaps C1 structurally | stays `FUTURE_RESEARCH` |

No candidate is promoted, rejected as predictive, or marked
`READY_FOR_REENTRY` by this structural battery. No new candidate ID was
created.

## Reproducibility and firewall

- Builder: `research/alpha_structural_robustness_v1.py`
- Builder SHA-256: `f87bb9ff9681148b48ea77d145a562d7bcfb4935cc1b9297b77e4358d0d460b1`
- Output: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_structural_robustness_v1.json`
- Output SHA-256: `5fdf09c2bf7b3897e14c5ff6f5d263eb58603512e399eac334db08d38b865505`
- Firewall artifact:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_structural_robustness_firewall_v2.json`
- Firewall artifact SHA-256: `03d9f76c5f7a666b8d41ec8ec08a0d94e9f5f8a6f0a77d85475d3dfdb234f2c2`
- Firewall result: `PASS`
- Python compilation: `PASS`
- Baseline formula equivalence: `PASS` with zero finite-pair difference.

All artifacts remain in the isolated staging root. No canonical, incumbent,
target, cloud, capture, scheduler, counter, or production artifact was
modified.

## Decision and next action

- Close monotone rank/z-score variants as duplicate representations; do not
  add them to the re-entry queue.
- Keep C1/C2/C4 fixed contracts unchanged, but record horizon choice as a
  genuine future-evaluation decision rather than a free parameter sweep.
- Keep C3 blocked pending financial PIT/source-capability remediation.
- The target-free economic/mechanism cards, re-entry packet, and independent
  red-team review are now recorded in the linked checkpoint documents. The
  remaining blockers are authoritative population/PIT admission and separate
  corporate-action/issuer-basis evidence; no target comparison follows from
  this structural battery.

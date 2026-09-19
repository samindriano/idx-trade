# Alpha Structural Lab V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `C_F_G_K_L_M_OUTCOME_BLIND_STRUCTURAL_LAB`  
Result: `PASS_STRUCTURAL_ONLY / NOT ALPHA EVIDENCE`

Post-Phase-Q note: this V1 artifact is retained for lineage. The diagnostic
return calculation was subsequently made explicit with
`pct_change(fill_method=None)`; the regenerated V2 artifact and hash are
recorded in `2026-09-19_ALPHA_PHASE_Q_REPLAY_RESULT_V1.md`.

## Question and non-redundancy rationale

The earlier economics audit answered fixed Top-30 turnover, concentration, and
first/last-half burden. It did not answer Top-10/20/50 mechanics, persistence,
rank churn, daily liquidity exposure, state-conditioned stability, or daily/
rolling candidate overlap. This lab answers those distinct structural questions
in one reusable pass over the same frozen C1–C4 ranks.

It does not read targets, forward returns, incumbent scores, provider data, or
protected outcomes. It does not tune any parameter or create a new candidate.

## Frozen inputs

- Window: 600 official sessions, `2024-01-12` through `2026-07-31`.
- Candidates: exactly C1, C2, C3, C4.
- Top-K: exactly 10, 20, 30, 50.
- Liquidity percentile: same-day eligible cross-sectional percentile of
  `regular_market_value`; no spread or queue data was present.
- Volatility state: high/low by frozen-window median daily median absolute
  close-to-close return.
- Liquidity state: high/low by frozen-window median daily median
  `regular_market_value`.
- Trend state: low/mixed/high by tertiles of the 20-session rolling sum of
  daily median close-to-close return.

## Top-K mechanics

Mean one-way turnover, mean consecutive-selection persistence, and the share of
selected slots in the bottom liquidity quartile are:

| Candidate | K | Turnover | Persistence (sessions) | Bottom-liquidity share |
|---|---:|---:|---:|---:|
| C1 | 10 | 47.88% | 2.08 | 26.7% |
| C1 | 20 | 44.45% | 2.25 | 26.5% |
| C1 | 30 | 42.15% | 2.37 | 26.6% |
| C1 | 50 | 38.11% | 2.62 | 27.0% |
| C2 | 10 | 35.93% | 2.78 | 15.5% |
| C2 | 20 | 34.00% | 2.93 | 19.0% |
| C2 | 30 | 32.91% | 3.03 | 21.3% |
| C2 | 50 | 31.45% | 3.17 | 23.3% |
| C3 | 10 | 13.14% | 7.44 | 12.2% |
| C3 | 20 | 12.03% | 8.11 | 14.8% |
| C3 | 30 | 10.93% | 8.41 | 16.5% |
| C3 | 50 | 10.38% | 9.29 | 14.9% |
| C4 | 10 | 29.25% | 3.41 | 39.4% |
| C4 | 20 | 25.71% | 3.87 | 35.7% |
| C4 | 30 | 23.70% | 4.20 | 34.5% |
| C4 | 50 | 20.43% | 4.86 | 32.8% |

The C3 persistence result is descriptive only and is dominated by sparse/late
financial coverage. It must not be interpreted as evidence of predictive
quality.

## Coverage, numerical stability, and rank churn

Within the frozen 600-session window, row coverage is C1 `99.52%`, C2
`100.00%`, C3 `19.91%`, and C4 `99.89%`. C3's lower in-window rate reflects
its late/sparse support and is consistent with its existing `BLOCKED` status.

Raw score tails are materially different:

| Candidate | Score skew | Score excess kurtosis | Mean absolute daily rank displacement | Structural flag |
|---|---:|---:|---:|---|
| C1 | 8.204 | 350.307 | 0.1527 | `MODERATE`: broad coverage, heavy raw tail, high churn |
| C2 | 19.545 | 1,466.359 | 0.1542 | `MODERATE`: broad coverage, very heavy raw tail |
| C3 | -0.149 | -0.486 | 0.0145 | `FRAGILE`: sparse/late support and concentration |
| C4 | -0.451 | 0.405 | 0.0787 | `MODERATE`: lower churn, liquidity and overlap cautions |

The tail result supports retaining rank-based future evaluation contracts. It
does not prove that a raw-score model would fail; it identifies raw-score
combination as numerically fragile without a separately frozen normalization.

## Rank versus liquidity relationship

Mean daily Spearman correlation between candidate rank and same-day liquidity
percentile is:

| Candidate | Rank vs market-value percentile | Rank vs volume percentile |
|---|---:|---:|
| C1 | -0.1331 | -0.1096 |
| C2 | 0.0211 | 0.0538 |
| C3 | 0.1873 | -0.0584 |
| C4 | -0.1940 | -0.1395 |

C1 and C4 tend structurally toward less-liquid names; C4 is the strongest of
the two on market-value rank. C2 is approximately liquidity-neutral in this
diagnostic. C3's value relationship is positive, but its support is not
population-complete.

## Temporal and market-state stability

Top-30 turnover by 100-session block:

| Candidate | Blocks 1 → 6 |
|---|---|
| C1 | 39.87%, 41.40%, 40.40%, 43.00%, 44.43%, 43.80% |
| C2 | 33.13%, 29.97%, 34.33%, 31.03%, 33.67%, 35.33% |
| C3 | no usable early blocks; 10.86%, 10.80%, 11.15% in blocks 4–6 |
| C4 | 22.69%, 20.90%, 23.23%, 22.90%, 27.37%, 25.07% |

Top-30 turnover in high/low structural states:

| Candidate | High vs low volatility | High vs low liquidity | Trend high / low / mixed |
|---|---|---|---|
| C1 | 42.78% / 41.53% | 41.70% / 42.61% | 42.27% / 41.63% / 42.52% |
| C2 | 34.23% / 31.58% | 31.57% / 34.26% | 30.72% / 35.82% / 32.25% |
| C3 | 11.36% / 10.17% | 9.00% / 12.28% | 8.48% / 14.16% / 10.09% |
| C4 | 24.18% / 23.21% | 22.84% / 24.55% | 22.72% / 23.97% / 24.35% |

These are structural mechanics, not regime-conditional returns.

## Structural orthogonality extension

Daily rank correlations and Top-30 same-day overlap were:

| Pair | Mean daily Spearman | Rolling-20 mean | Rolling-60 mean | Top-30 overlap | Top-30 Jaccard |
|---|---:|---:|---:|---:|---:|
| C1 / C2 | -0.2454 | -0.2471 | -0.2576 | 12.21% | 6.77% |
| C1 / C3 | -0.0281 | -0.0275 | -0.0284 | 10.30% | 5.55% |
| C1 / C4 | 0.4624 | 0.4624 | 0.4659 | 34.89% | 21.57% |
| C2 / C3 | -0.0366 | -0.0332 | -0.0299 | 8.62% | 4.62% |
| C2 / C4 | -0.1494 | -0.1488 | -0.1544 | 11.00% | 6.03% |
| C3 / C4 | -0.0437 | -0.0442 | -0.0425 | 9.47% | 5.09% |

Implications are structural only:

- C1/C4 are the clearest likely duplicate-mechanism pair and should not be
  treated as automatically additive.
- C1/C2 and C2/C4 have low overlap and opposite rank dependence, making them
  plausible future combination hypotheses.
- C3 is structurally distinct, but its sparse/late support prevents it from
  entering the evaluation queue now.
- Low correlation/overlap is not proof of predictive orthogonality.

## Structural disposition

| Candidate | Structural label | Reason |
|---|---|---|
| C1 | `FUTURE_RESEARCH` / `MODERATE` | broad coverage; high churn; heavy raw tail; modest low-liquidity tilt |
| C2 | `FUTURE_RESEARCH` / `MODERATE` | full coverage; lower churn than C1; very heavy raw tail; near liquidity-neutral |
| C3 | `BLOCKED` / `FRAGILE` | sparse/late PIT support and concentration despite persistence |
| C4 | `FUTURE_RESEARCH` / `MODERATE` | lowest broad-candidate churn; strongest low-liquidity tilt; overlaps C1 |

No candidate is structurally rejected by this lab. No candidate is upgraded to
`READY_FOR_REENTRY` or `RESEARCH_SURVIVOR`.

## Reusable tooling and reproducibility

- Builder: `research/alpha_structural_lab_v1.py`
- Builder SHA-256: `8d8acad19bf5fcf60cb4f147b8ef7e92ffc7b080cb8182baaf1550f531d10b47`
- Independent verifier: `research/verify_alpha_structural_lab_v1.py`
- Verifier SHA-256: `2c310d8b5102d8b4b406d9f9fd14c787def69208c1e59d16a78153398ee15eab`
- Output: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_structural_lab_v1.json`
- Output SHA-256: `f53978403ba831e85f75ca918d0c3524259b226ffdd319d274434b328f6b5de5`
- Python compilation: `PASS`
- Independent structural verifier: `PASS`
- Target firewall: `PASS` after including both structural lab scripts and the
  output JSON; firewall audit SHA-256
  `211d78f5a1ece63a4b1a5ac7d76ac54e70b550961253aa74dccf700240b59d91`.

# Alpha Combination Readiness and Economics Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `M_COMBINATION_READINESS_L_IMPLEMENTATION_ECONOMICS`
Result: `PASS_STRUCTURAL_ONLY / NO NEW CANDIDATE ID`

## Question and boundary

Can structurally distinct fixed candidates be combined without optimizing
weights, using only already frozen C1/C2/C4 rank columns? This study measures
selection complementarity, turnover diversification, liquidity exposure, and
fixed friction sensitivity. It does not use targets, returns, incumbent
scores, future outcomes, or optimized ensemble weights.

The exact equal-weight set is:

- `C1_C2_EW = mean(rank_C1, rank_C2)`;
- `C1_C4_EW = mean(rank_C1, rank_C4)`;
- `C2_C4_EW = mean(rank_C2, rank_C4)`;
- `C1_C2_C4_EW = mean(rank_C1, rank_C2, rank_C4)`.

These are future combination hypotheses, not C5+ candidates.

## Top-30 results

| Combination | Mean turnover | Base burden | Low burden | Stress burden | Top-10 slot share |
|---|---:|---:|---:|---:|---:|
| C1+C2 | 42.14% | 25.28 bps/NAV | 16.85 | 46.35 | 6.11% |
| C1+C4 | 34.85% | 20.91 bps/NAV | 13.94 | 38.33 | 6.69% |
| C2+C4 | 36.70% | 22.02 bps/NAV | 14.68 | 40.37 | 6.27% |
| C1+C2+C4 | 37.95% | 22.77 bps/NAV | 15.18 | 41.75 | 6.19% |

The burden scenarios are fixed structural sensitivities:

- Low: 10 bps buy fee, 20 bps sell fee, 5 bps slippage per side = 40 bps;
- Base: 15 bps buy fee, 25 bps sell fee, 10 bps slippage per side = 60 bps;
- Stress: 40 bps buy fee, 50 bps sell fee, 10 bps slippage per side = 110 bps.

They are not realized costs or profitability claims.

## Complementarity and implementation

Mean Top-30 overlap with components:

| Combination | Component overlaps | Component overlap below 50% |
|---|---|---|
| C1+C2 | C1 45.11%, C2 26.68% | C1 61.5%, C2 83.5% of dates |
| C1+C4 | C1 63.29%, C4 59.86% | C1 5.5%, C4 9.0% |
| C2+C4 | C2 29.06%, C4 45.83% | C2 87.8%, C4 59.5% |
| C1+C2+C4 | C1 45.48%, C2 23.17%, C4 45.61% | C1 61.0%, C2 93.8%, C4 60.7% |

The C1+C4 combination is the most conservative compromise in this structural
view: it retains more than half of each component's Top-30 set on most dates
and has the lowest combination turnover. The other combinations materially
change the selected set, especially relative to C2. This demonstrates
selection complementarity, not incremental predictive information.

Selected bottom-quartile exposure is low in this panel for all combinations:
bottom market-value share is `0.43%`–`0.71%`, and bottom volume share is
`1.44%`–`1.67%`. Top-10 ticker slot share is `6.11%`–`6.69%`, with no
single-name slot share above `0.86%`. These are structural panel diagnostics;
they do not certify historical liquidity, spread, queue position, or capacity.

## Disposition

| Question | Result |
|---|---|
| Equal-weight combinations structurally distinct? | Yes, especially C1+C2/C2+C4 versus their C2 component; not a predictive claim. |
| Weight optimization justified? | No; prohibited by this packet. |
| New candidate IDs? | No. |
| Combination ready for protected evaluation? | Conditional only; C1+C4 is the cleanest structural combination hypothesis, still pending the same Data QA and target admission as its components. |
| Structural rejection? | None solely from these diagnostics. |

## Reproducibility and firewall

- Research commit: `0a9bbbb9` (artifact replay/current-lane pin)
- Builder: `research/alpha_combination_economics_v1.py`
- Builder SHA-256: `a326d8d40933562f2de3a3137adc2a0280529d3db610ed2c6ce5224b73568591`
- Independent verifier: `research/verify_alpha_combination_economics_v1.py`
- Independent verifier SHA-256: `3e8b7ad0a2cc3d760bd56f0838c1a2e76878bc9e97ba86c257159e33aa0889bc`
- Output:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_combination_economics_v1.json`
- Output SHA-256: `82c76798f5135f345e41f9d536497f68908b3744107d951b583d6a3297de985d`
- Firewall artifact:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_combination_economics_firewall_v1.json`
- Firewall artifact SHA-256: `4d00cace99225d5286c5143698622a85a735564b5ee6955bab98007038d679f4`
- Verifier, firewall, and Python compilation: `PASS`

No target, forward return, incumbent score, provider, network, cloud, capture,
scheduler, counter, canonical, or production artifact was opened or modified.

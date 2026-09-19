# H-LIQ-01 Robustness Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `Q_HLIQ01_ADVERSARIAL_ROBUSTNESS`
Result: `PASS_STRUCTURAL_ONLY / STATUS UNCHANGED`

## Scope

This is the bounded red-team follow-up for H-LIQ-01. It addresses the open
questions identified by independent review: horizon sensitivity, conditional
redundancy by market-value bucket, synthetic missingness, persistence, and
listing-age concentration. Sector analysis is explicitly unavailable because
no admissible sector field is present in the local panel.

No target, forward return, incumbent score, provider, network, or protected
artifact was opened. No C5 ID was created.

## Horizon sensitivity

The fixed prototype is H-LIQ-01 h20. Relative to its Top-30 sets:

| Horizon | Mean Top-30 turnover | Mean overlap vs h20 |
|---|---:|---:|
| h10 | 16.83% | 61.13% |
| h20 fixed | 10.31% | 100.00% |
| h40 | 6.90% | 62.02% |

All horizons have 155,679 finite rows over 600 dates and 583 tickers. Horizon
is therefore a real representation choice, but h10/h40 are not completely
independent mechanisms. No horizon was selected or promoted from this result.

## Conditional redundancy by liquidity bucket

Mean daily Spearman dependence between H-LIQ-01 and fixed candidates, within
same-day market-value quartiles:

| Value bucket | H-LIQ/C1 | H-LIQ/C2 | H-LIQ/C4 |
|---|---:|---:|---:|
| Q1 bottom value | 0.009 | 0.045 | -0.035 |
| Q2 | -0.030 | 0.032 | -0.140 |
| Q3 | -0.096 | 0.100 | -0.184 |
| Q4 top value | -0.174 | 0.196 | -0.244 |

The C2 relationship is low in the lower three buckets but rises in the top
value bucket. This supports “potentially distinct, shared participation
ingredients” rather than either “identical” or “proven orthogonal.” C1/C4
dependence remains low within every bucket.

## Synthetic missingness stress

All three stress levels retained 600 usable Top-30 dates:

| Mask rate | Finite-row loss | Mean Top-30 overlap vs h20 |
|---:|---:|---:|
| 0.5% | 0.529% | 99.49% |
| 1% | 1.024% | 98.90% |
| 5% | 5.007% | 94.93% |

This is a deterministic sensitivity test, not a model of source missingness or
PIT completeness.

## Listing-age concentration

Using the reconciled security master only as an identity/listing interval
sidecar:

- all finite eligible H-LIQ rows had a mapped `listed_from`;
- 0% of eligible rows were listed within the prior 60 calendar days;
- 5.51% of eligible rows were listed within the prior 365 days;
- 11.22% of H-LIQ selected slots were from names listed within the prior 365
  days;
- 0% of selected slots were from names listed within the prior 60 days.

The selected/eligible ratio indicates some new-listing concentration, but does
not establish survivorship or corporate-action correctness. The corporate-
action basis remains a separate blocked admission risk.

## Adversarial disposition

| Review item | Result |
|---|---|
| Target/provider/network firewall | `PASS` |
| H-LIQ missingness robustness | `PASS_STRUCTURAL_ONLY` |
| H-LIQ horizon robustness | `MODERATE`; h10/h40 differ materially from h20 |
| Conditional novelty vs C2 | `UNRESOLVED`; dependence rises in Q4 |
| Small-cap/liquidity exposure | `CAUTION`; prior bottom-value share 39.67% remains |
| Listing-age concentration | `CAUTION`; selected share exceeds eligible share for ≤365 days |
| Sector robustness | `UNKNOWN/BLOCKED`; no sector field admitted |
| Candidate admission | `NO`; remains no C5 |

Final disposition remains:
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`.

## Reproducibility and firewall

- Builder: `research/alpha_hliq01_robustness_v1.py`
- Builder SHA-256: `06602fab5c682eee3b20ab33e2bba8f4bdae9c19331cd1f23f88e3e1e3f496bb`
- Output:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_hliq01_robustness_v1.json`
- Output SHA-256: `76df1eae63edcee51cd3def931cb5e6dd6d53681b158c888b192344a1b613c79`
- Firewall artifact:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_hliq01_robustness_firewall_v1.json`
- Firewall artifact SHA-256: `15b90cf2959371e370efc344b14e5a90fe6c4818083797ee6f55173513d05a08`
- Firewall result: `PASS`
- Python compilation: `PASS`

No candidate status was upgraded, no target was read, and no canonical or
production artifact was modified.

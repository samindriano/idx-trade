# Alpha Capacity Proxy Stress Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `L_CAPACITY_PROXY_STRESS`
Result: `PASS_STRUCTURAL_ONLY / CAPACITY REMAINS UNADMITTED`

## Question and boundary

How sensitive is the coarse per-selected-name capacity proxy to reasonable
participation rates? The analysis uses only frozen `regular_market_value` and
the fixed C1-C4 Top-30 selections. Rates are `0.25%`, `0.5%`, `1%`, and `2%` of
regular market value.

This is not ADV, traded value, spread, queue position, executable capacity, or
profitability. It does not use targets, returns, incumbent scores, providers,
or future outcomes.

## Q10 capacity proxy by participation rate

Values are IDR per selected name, tenth percentile across selected slots.

| Candidate | 0.25% | 0.5% | 1% | 2% |
|---|---:|---:|---:|---:|
| C1 | 1,907,722 | 3,815,444 | 7,630,887 | 15,261,774 |
| C2 | 1,600,810 | 3,201,621 | 6,403,241 | 12,806,483 |
| C3 | 3,256,617 | 6,513,234 | 13,026,468 | 26,052,936 |
| C4 | 1,255,675 | 2,511,350 | 5,022,700 | 10,045,399 |

All selected slots had finite positive `regular_market_value` in this frozen
panel. C4 has the lowest q10 proxy across every rate, while C3 has the highest
proxy but remains unusable for broad historical comparison because its support
is sparse and late.

## Interpretation

- The result strengthens the existing economic caution for C4: its lower
  capacity proxy is consistent with a less liquid/less scalable selected tail.
- C1 and C2 are intermediate and differ in turnover/cost, so no single
  structural metric establishes a preferred candidate.
- C3's apparently favorable capacity proxy cannot rescue its PIT/coverage
  block.
- The exact rate sensitivity is mechanical; it does not validate the rate as
  a realistic market-participation limit.

## Disposition

| Item | Status |
|---|---|
| Structural capacity sensitivity | `COMPLETE` for permitted value proxy |
| Historical ADV/spread/queue/capacity | `UNKNOWN/BLOCKED` |
| Candidate status changes | None |
| New candidate IDs | None |
| Target/provider/network access | None |

## Reproducibility and firewall

- Research commit: `5d1f97c6`
- Builder: `research/alpha_capacity_stress_v1.py`
- Builder SHA-256: `3da7292c5504f7325f09a9f693cda359ff1b095c2249a7dce7578c306904fb81`
- Independent verifier: `research/verify_alpha_capacity_stress_v1.py`
- Independent verifier SHA-256: `1fc541c5aec9989b8b5f058b642479cb8b2e7bbbb4097103849cb8e28bd05816`
- Output:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_capacity_stress_v1.json`
- Output SHA-256: `6fd5539964a39109b44dca6769a4556e7e8f78d88b2d277790332622dfeb93fb`
- Firewall artifact:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_capacity_stress_firewall_v1.json`
- Firewall artifact SHA-256: `acbe5c8e1d20d1d28a7be429351650d944506542fc7f2a068d27590383b5e7f4`
- Compilation, verifier, and firewall: `PASS`

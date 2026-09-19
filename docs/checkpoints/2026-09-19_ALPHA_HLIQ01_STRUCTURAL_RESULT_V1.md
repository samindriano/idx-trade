# H-LIQ-01 Structural Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Hypothesis card: `H-LIQ-01`  
Result: `PASS_STRUCTURAL_ONLY / FUTURE_RESEARCH / NOVELTY_PENDING`

## Scope

H-LIQ-01 tests one target-free representation of trading-activity
variability:

`rolling_20_std(log(close * volume))`

Higher values are ranked first. This is deliberately one fixed prototype, not
a lookback sweep and not candidate `C5`. It asks whether a variability-of-
activity state is structurally different from the fixed C1/C2/C3/C4 scores and
whether its portfolio mechanics are usable enough to justify further work.

The mechanism is motivated by the literature card pack, especially the
distinction between trading-activity level and variability. Literature is
inspiration only; this result is local IDX structural evidence, not predictive
evidence.

## Structural result

On the frozen 600-session window (`2024-01-12`–`2026-07-31`):

- finite rows: `155,679`;
- dates: `600`;
- tickers: `583`;
- Top-30 mean one-way turnover: `10.31%`;
- Top-30 turnover Q10–Q90: `3.33%`–`16.67%`;
- score skew: `1.589`;
- excess kurtosis: `5.712`.

The low turnover is structurally attractive, but it is not a profitability
claim.

## Dependence and overlap

| Fixed candidate | Mean daily Spearman | Mean Top-30 overlap |
|---|---:|---:|
| C1 | -0.0453 | 8.97% |
| C2 | 0.0996 | 31.34% |
| C3 | -0.1259 | 4.75% over 278 usable Top-30 dates |
| C4 | -0.1050 | 12.48% |

The prototype is not a monotone duplicate of C1 or C4. Its overlap with C2 is
meaningful but not identity-level; this is consistent with shared use of
turnover information and does not prove incremental predictive information.

## Liquidity and implementation caution

- Daily rank vs market-value percentile: `-0.2537`.
- Daily rank vs volume percentile: `-0.0388`.
- Selected Top-30 slots in bottom market-value quartile: `39.67%`.
- Selected Top-30 slots in bottom volume quartile: `27.58%`.

The candidate is therefore low-churn but materially tilted toward smaller
market-value names. A future evaluation would require a more realistic
liquidity/capacity contract; the existing coarse friction proxy is not enough
to call this economically ready.

## Novelty decision

`H-LIQ-01` remains a future-research direction, not a new candidate ID.

Reasons to retain the card:

- its temporal mechanism differs from C2's level-of-participation
  confirmation;
- its daily dependence with C1/C4 is low and its Top-30 overlap with them is
  small;
- it has full broad-candidate coverage in this frozen window and much lower
  churn than C1/C2/C4.

Reasons not to admit C5 yet:

- only one representation has been tested;
- the mechanism uses the same raw turnover ingredients as C2;
- bottom-liquidity exposure is high;
- no target, OOS, IC/ICIR, incumbent comparison, or prospective evidence is
  available;
- independent red-team review and a frozen future evaluation contract are not
  complete.

Disposition: `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`.

## Exact next action

Before any candidate-ID decision, perform one independent review of:

1. turnover-unit and price-basis semantics;
2. listing/delisting and missingness concentration;
3. C2 conditional redundancy after controlling only for structural rank and
   liquidity buckets;
4. capacity/friction scenarios using the already permitted structural fields.

No parameter sweep, target access, or provider/source expansion is authorized by
this result.

## Reproducibility and firewall

- Builder: `research/alpha_hliq01_structural_v1.py`
- Builder SHA-256: `389f54762a3dd3871c2261ac66a8a26082478e1028288a676a6c8f019449bb7f`
- Output: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_hliq01_structural_v1.json`
- Output SHA-256: `0a851cc201fb6b764c833f03e616611d5cdc6909894fc8103945e3678fbd6a9e`
- Firewall artifact:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_hliq01_structural_firewall_v1.json`
- Firewall artifact SHA-256: `937bf9b3557bcbda57db01b10d3ed13c605bd9f7f998156833abbf3287295ba0`
- Firewall result: `PASS`
- Python compilation: `PASS`

No protected target, forward return, incumbent score, provider, network,
canonical, cloud, capture, scheduler, counter, or production artifact was
opened or modified.

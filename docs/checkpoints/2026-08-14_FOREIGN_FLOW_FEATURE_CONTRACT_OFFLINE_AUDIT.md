# Foreign Flow Feature Contract V1 — Offline Materialization Audit

Status: `REVIEW`

Branch: `research/idx-foreign-flow-feature-contract-v1`

Initial audit base: `f4d997c55f90c86a72dbad2719c6ad30a08919d4`

Remediated from reviewed HEAD `c000824f253fef41065edbe696811016d20392fe`.

## Scope and boundaries

This checkpoint covers feature-contract definition and offline materialization
only. No provider calls, outcome reads, performance tests, model fitting,
forward counters, or changes to Financial PIT, Corporate Actions, O2, or
protected artifacts were made.

The accepted foreign-flow archive is:

- archive root: `D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1`;
- window: 2021-04-01 through 2026-08-13;
- 1,288 official sessions, 1,129,024 normalized rows, 983 tickers;
- unit: `SHARES`;
- provenance: `OFFICIAL_IDX_HISTORICAL_EOD / RETROSPECTIVELY_ACQUIRED`;
- archive manifest SHA-256:
  `fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`.

The denominator is the existing official IDX Stock Summary cache, not Yahoo:
the regular-market `volume` field only. `nonregular_volume`, frequency, value,
OHLC, and same-session close are not consumed. The cache covers 1,260 sessions
from 2021-04-29 through 2026-07-31 and has 980 tickers. The existing PIT
security master has 979 tickers.

## Frozen feature contract

For signal/session `t`, features are materialized on the next official session
`t+1`; only exact official sessions through `t` are eligible. No same-session
close is used and no calendar-day resampling or forward-fill is used.

The materialized columns are:

| Feature | Definition |
| --- | --- |
| `foreign_net_to_volume_1` | `ForeignNet[t] / RegularVolume[t]` |
| `foreign_net_to_volume_sum_N` | `sum(ForeignNet[t-N+1:t]) / sum(RegularVolume[t-N+1:t])`, `N ∈ {3,5,10,20}` |
| `foreign_sign_consistency_N` | mean of `sign(ForeignNet)` over the prior `N` official sessions, with zero flow as sign 0 |
| `foreign_flow_acceleration_3_20` | `foreign_net_to_volume_sum_3 - foreign_net_to_volume_sum_20` |
| `foreign_gross_to_volume_1` | `(ForeignBuy[t] + ForeignSell[t]) / RegularVolume[t]` |

Zero foreign flow is valid. A feature is missing when an exact required flow or
volume observation is absent, listing history has a gap, history is shorter
than the window, or the regular-volume denominator is invalid/zero. Ambiguous
or non-lineage rows fail closed. No clipping, winsorization, ranking, or
own-history normalization is applied in this stage.

## Offline result

The output is 1,102,650 candidate rows over 1,259 feature sessions
(2021-04-30 through 2026-07-31) and 979 tickers:

- fully available: 964,078 rows (87.44%);
- partial: 137,592 rows (12.48%);
- missing: 980 rows (0.09%).

Year-level availability:

| Year | Candidate rows | Available | Partial | Missing | Available rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 123,886 | 97,918 | 25,447 | 521 | 79.04% |
| 2022 | 195,828 | 173,706 | 21,818 | 304 | 88.70% |
| 2023 | 208,328 | 183,555 | 24,694 | 79 | 88.11% |
| 2024 | 220,212 | 195,256 | 24,914 | 42 | 88.67% |
| 2025 | 225,155 | 198,682 | 26,447 | 26 | 88.24% |
| 2026 through 2026-07-31 | 129,241 | 114,961 | 14,272 | 8 | 88.95% |

The dominant structural missingness is zero regular-market volume for the
one-day ratio features (120,723 rows), plus missing-window input affecting the
20-session acceleration (106,908 rows). These are retained as explicit
diagnostics, not converted to zero or filled. Sign-consistency features remain
available when exact flow history exists even if a volume denominator is not
usable.

The exact 28 archive sessions outside the materialized common-input window,
derived from the accepted flow-session set minus the official volume-session
set, are:

`2021-04-01`, `2021-04-05`, `2021-04-06`, `2021-04-07`, `2021-04-08`,
`2021-04-09`, `2021-04-12`, `2021-04-13`, `2021-04-14`, `2021-04-15`,
`2021-04-16`, `2021-04-19`, `2021-04-20`, `2021-04-21`, `2021-04-22`,
`2021-04-23`, `2021-04-26`, `2021-04-27`, `2021-04-28`, `2026-08-03`,
`2026-08-04`, `2026-08-05`, `2026-08-06`, `2026-08-07`, `2026-08-10`,
`2026-08-11`, `2026-08-12`, `2026-08-13`.

No weekday or calendar-day inference was used.

They were not materialized because the accepted local official Stock Summary
volume cache stops at 2021-04-29 and 2026-07-31. No network call or substitute
volume source was used. This is an explicit coverage limitation of this audit.

## Artifacts

External artifacts are under
`D:\Documents\Project\idx-trade-foreign-flow-feature-contract-20260814-v1`.

| Artifact | SHA-256 |
| --- | --- |
| `foreign_flow_features.parquet` | `059471948ad9efb5b2343d9aed729d04c5e3f2c01881153679db579b3a1d1733` |
| `materialization_manifest.json` | `8c45bb42cc9bda4002967f8bc5fd5509842947dbaa3e1f764e925cbe0f8ccd1a` |
| `offline_feature_audit_manifest.json` | `2341df7d7ff646dc8a13da2a45e9220e0c4c569017b373ca72daed18dcb377e4` |
| `coverage_by_session.csv` | `b99bf46af5ac6a09a72c0bc22832ab6ec4d3b70ea53fb1f499c3ee3d8a9ac07e` |
| `coverage_by_ticker.csv` | `6cc28ae4b9e3b4fdb0f4f07c53dab90aa26f894ad43f82391861fdc5985090bc` |
| `coverage_by_year.csv` | `a1fbef586dfc85d96265225f111fe3bea73f8d063ad956148736d006c8c71309` |
| `feature_distribution.csv` | `748b76104a518409d719b8b4a80e4b2474ceb2570870e418bd4e29a2c7a25a83` |
| `missing_reason_counts.csv` | `3eb7a2d321bc961f0bd2613af977f0cbd60d8f2986932f5726e6142b45bb9e36` |

## Validation

- focused feature tests: `9 passed`;
- full IDX-Trade pytest from this worktree: `49 collected, 48 passed, 1 failed`;
- the single failure is the unrelated storage expectation documented in the
  causal-remediation checkpoint; the prior audit's `47 passed` result predates
  this remediation run;
- `git diff --check`: passed;
- causality regression: changing flow on session `t+1` does not change the
  feature row for `t+1`; the feature row uses flow only through `t`;
- source audit: official Stock Summary regular `volume` is the only volume
  denominator; Yahoo/raw OHLCV was not used.

## Causal remediation

`foreign_gross_to_volume_1` now uses the exact prior-session arrays, so for
feature session `t+1` it is `(ForeignBuy[t] + ForeignSell[t]) /
RegularVolume[t]`. Regression tests cover all feature columns against changes
to same-session flow/volume, prior-session gross-flow response, rolling
windows, sign consistency, acceleration, and one-day net causality.

The prior feature parquet SHA
`fbfe79290270d3f9955a81366352e9b3615dd4bd61e73848bdb345154ac056f9` is no
longer authoritative. The rematerialized artifact is the SHA listed above.

## Decision

`FOREIGN_FLOW_FEATURE_CONTRACT_V1_OFFLINE_AUDIT_READY_FOR_REVIEW`.

The feature family is frozen for independent review and future outcome testing,
but outcome/performance testing is not authorized by this checkpoint. The
2021-04-01..2021-04-28 and 2026-08-03..2026-08-13 archive sessions remain
outside the materialized feature panel until an already-authorized canonical
volume artifact exists; this lane does not acquire it.

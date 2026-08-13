# Foreign Flow Feature Contract V1 — Offline Materialization Audit

Status: `REVIEW`

Branch: `research/idx-foreign-flow-feature-contract-v1`

Base: `f4d997c55f90c86a72dbad2719c6ad30a08919d4`

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

- fully available: 951,315 rows (86.28%);
- partial: 150,355 rows (13.64%);
- missing: 980 rows (0.09%).

Year-level availability:

| Year | Candidate rows | Available | Partial | Missing | Available rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 123,886 | 96,394 | 26,971 | 521 | 77.81% |
| 2022 | 195,828 | 170,737 | 24,787 | 304 | 87.19% |
| 2023 | 208,328 | 180,105 | 28,144 | 79 | 86.45% |
| 2024 | 220,212 | 192,393 | 27,777 | 42 | 87.37% |
| 2025 | 225,155 | 197,191 | 27,938 | 26 | 87.58% |
| 2026 through 2026-07-31 | 129,241 | 114,495 | 14,738 | 8 | 88.59% |

The dominant structural missingness is zero regular-market volume for the
one-day ratio features (120,723 rows), plus missing-window input affecting the
20-session acceleration (106,908 rows). These are retained as explicit
diagnostics, not converted to zero or filled. Sign-consistency features remain
available when exact flow history exists even if a volume denominator is not
usable.

The 28 archive sessions outside the materialized common-input window are:

- 2021-04-01 through 2021-04-28: 20 sessions;
- 2026-08-03 through 2026-08-13: 9 sessions.

They were not materialized because the accepted local official Stock Summary
volume cache stops at 2021-04-29 and 2026-07-31. No network call or substitute
volume source was used. This is an explicit coverage limitation of this audit.

## Artifacts

External artifacts are under
`D:\Documents\Project\idx-trade-foreign-flow-feature-contract-20260814-v1`.

| Artifact | SHA-256 |
| --- | --- |
| `foreign_flow_features.parquet` | `fbfe79290270d3f9955a81366352e9b3615dd4bd61e73848bdb345154ac056f9` |
| `materialization_manifest.json` | `09102f0cd41a59dbd4392b6e15356ccb9bcc3e23ccd8ada3977b3a0fa0050957` |
| `offline_feature_audit_manifest.json` | `55a983fa0f9463429b10e493cef7da95b96f589ab6a6d9de7a52ad7d4bb6a714` |
| `coverage_by_session.csv` | `bc3056a70be0e4811611eb10c703d3a32db7cdf39170bf3e03ae1242ca2dab9d` |
| `coverage_by_ticker.csv` | `f799942dd56f29711cf306d4053d3b5304e3e6b788074e33f2c6853ba77bc24c` |
| `coverage_by_year.csv` | `ee0edda2f8abb5fbdd6ff962460d68141f9d503f26f67e9c48ac889c65f4b2d3` |
| `feature_distribution.csv` | `3c291098db2d207a77f69f67cbb294f9945e61c1794304faf3c87cfa1ba35c6a` |
| `missing_reason_counts.csv` | `3eb7a2d321bc961f0bd2613af977f0cbd60d8f2986932f5726e6142b45bb9e36` |

## Validation

- focused feature tests: `7 passed`;
- full IDX-Trade pytest from this worktree: `47 passed`;
- `git diff --check`: passed;
- causality regression: changing flow on session `t+1` does not change the
  feature row for `t+1`; the feature row uses flow only through `t`;
- source audit: official Stock Summary regular `volume` is the only volume
  denominator; Yahoo/raw OHLCV was not used.

## Decision

`FOREIGN_FLOW_FEATURE_CONTRACT_V1_OFFLINE_AUDIT_READY_FOR_REVIEW`.

The feature family is frozen for independent review and future outcome testing,
but outcome/performance testing is not authorized by this checkpoint. The
2021-04-01..2021-04-28 and 2026-08-03..2026-08-13 archive sessions remain
outside the materialized feature panel until an already-authorized canonical
volume artifact exists; this lane does not acquire it.

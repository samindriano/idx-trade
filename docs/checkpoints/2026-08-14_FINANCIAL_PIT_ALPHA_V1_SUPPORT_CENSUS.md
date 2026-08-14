# Financial PIT Alpha V1 support census

Branch: `research/idx-financial-pit-alpha-v1`

Stage: outcome-blind preregistration and support census only.

## Result

The support census completed with the exact fiscal-year and knowledge-time
join contract. The later model comparison row set is frozen as:

- 70,556 V2 rows;
- 321 tickers;
- support rule: `any_feature_available_at_least_one_period_stratum`;
- comparison support key SHA-256:
  `fbb78032a9ce00f79dbc933ce0a806af36f1ebcef7a3352598f0e60e7d4de303`;
- identity key SHA-256: `21c42b5210cff2d73a494c3980a89b665add894cb8a7f8a467d655eb12026007`.

The support set is frozen before any target, score, or performance artifact is
opened. It can be replaced only by a separately reviewed preregistration.

## Inputs and output manifest

- V2 common support SHA-256:
  `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`.
- Financial feature panel SHA-256:
  `1d60ee69070546d21040af8c61f2170c5cca2254f131626a19bf4c1d59f3f023`.
- Financial panel manifest SHA-256:
  `639fc6e6fe3f7f853d23b6f5244c98ec8ed5c63b219aa59e698c8db908fb2140`.
- Census root:
  `D:\Documents\Project\idx-financial-pit-alpha-20260814-v1-census-v4`.
- Support census manifest SHA-256:
  `3db7c314cf6e84bdd631b8e86b674a4bcca05813d5601a11420d9107b3785a84`.

## Census coverage

The V2 parent has 277,244 rows, 729 tickers, dates 2021-06-02 through
2026-07-17, and signal sessions 20..1250. The accepted Financial panel has
258,401 rows, 531 tickers, and 7,722 unique ticker/fiscal-year/as-of states.

Rows with any Financial state: 90,526. Rows with at least one available feature
state: 70,556. Knowledge-time violations: 0. Same-day publication cases:
1,377. Same-knowledge-time conflict keys: 6, producing 52 ambiguous support
rows that remain fail-closed. Latest filing age among rows with any state:
min 0.000231481, median 54.3538310185, q25 25.30858217575, q75
88.5383275465, max 626.590138889 days.

Calendar-year coverage:

| V2 year | rows | any state | any feature | issuers |
|---:|---:|---:|---:|---:|
| 2021 | 29,199 | 0 | 0 | 338 |
| 2022 | 56,092 | 0 | 0 | 446 |
| 2023 | 50,346 | 0 | 0 | 408 |
| 2024 | 47,953 | 17,735 | 13,973 | 373 |
| 2025 | 54,873 | 42,539 | 33,181 | 489 |
| 2026 | 38,781 | 30,252 | 23,402 | 504 |

Period-stratum coverage in selected state rows:

| Stratum | selected state rows | V2 rows | issuers | available state rows | ambiguous |
|---|---:|---:|---:|---:|---:|
| Q1 | 1,268,462 | 68,005 | 376 | 729,585 | 0 |
| H1 | 1,536,223 | 80,202 | 397 | 917,348 | 0 |
| 9M | 1,306,331 | 72,750 | 382 | 757,582 | 0 |
| FY | 948,467 | 59,196 | 379 | 540,465 | 156 |

The exact per-feature × period counts are in the external
`feature_support.csv`; the census preserves them without collapsing period
strata. The external ticker audit covers all 729 tickers; 321 have at least
one available feature state. The top 10 tickers account for 6.5749192131% of
available-support rows; no concentration gate has been interpreted as a model
result.

## Safety status

`performance_metrics_computed=false`, `model_fit=false`,
`outcomes_accessed=false`, `fresh_forward_accessed=false`, and provider calls
were zero. No protected label parquet, O2/V3-B rescore, or model artifact was
opened. The remaining ambiguity and sparse pre-2024 support are documented for
review; this checkpoint does not declare the Financial family scientifically
useful or authorize an experiment run.

## Validation

- Focused Alpha tests: 7 passed.
- Full repository pytest: 57 passed, 1 failed at the unrelated existing
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.
  The current storage contract surfaces two independent conflicts
  (`raw_close` and `vendor_adj_close`) while that legacy test expects one. This
  lane did not modify storage or that test.

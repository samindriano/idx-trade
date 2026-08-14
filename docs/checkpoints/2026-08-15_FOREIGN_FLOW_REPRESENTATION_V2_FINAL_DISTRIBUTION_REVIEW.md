# Foreign Flow Representation V2 — Final Distribution/Behavior Review

Date: 2026-08-15 (Asia/Jakarta)
Branch: `research/idx-foreign-flow-representation-v2`
Starting HEAD: `5c0bba250d9aac3b4789416080e4c242e9a2bb44`
Status: `REVIEW`

## Scope

This is a read-only, outcome-blind audit of the already materialized V2
artifacts. No formula, feature parquet, provider source, model, score, label,
H10 metric, V1 alpha result, protected outcome, or fresh-forward artifact was
accessed or changed. No rematerialization was performed.

External output root:
`D:\Documents\Project\idx-trade-foreign-flow-representation-v2-20260815-001`

Existing output manifest SHA-256:
`4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc`

## Full feature distribution

Values below are read directly from `feature_distribution.csv`.

| Feature | Finite | Missing | Min | P01 | Q25 | Median | Q75 | P99 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `foreign_participation_1` | 981109 | 121291 | -1.000000 | -0.666667 | -0.023483 | 0.000000 | 0.008513 | 0.604792 | 1.000000 |
| `foreign_participation_mean_5` | 942516 | 159884 | -1.000000 | -0.433303 | -0.029139 | 0.000000 | 0.017078 | 0.373037 | 1.000000 |
| `foreign_flow_shock_1` | 963971 | 138429 | -41719.091451 | -1.629727 | -0.023934 | 0.000000 | 0.009886 | 1.178470 | 62062.306900 |
| `foreign_flow_shock_mean_5` | 930448 | 171952 | -13038.816181 | -1.542485 | -0.033008 | 0.000000 | 0.020413 | 0.946044 | 15786.679712 |
| `foreign_flow_shock_mean_20` | 870581 | 231819 | -3985.855287 | -1.421136 | -0.036672 | 0.000000 | 0.019180 | 0.809857 | 3946.175481 |
| `foreign_flow_shock_percentile_120` | 899158 | 203242 | 0.000000 | 0.000000 | 0.308333 | 0.500000 | 0.675000 | 1.000000 | 1.000000 |
| `xs_rank_foreign_flow_shock_1` | 347837 | 754563 | 0.002309 | 0.011952 | 0.251825 | 0.501880 | 0.751825 | 0.991935 | 1.000000 |
| `xs_rank_foreign_flow_shock_mean_5` | 346420 | 755980 | 0.002315 | 0.011933 | 0.251873 | 0.501873 | 0.751825 | 0.991931 | 1.000000 |
| `xs_rank_foreign_flow_shock_mean_20` | 336691 | 765709 | 0.002375 | 0.012011 | 0.251852 | 0.501916 | 0.751908 | 0.991838 | 1.000000 |
| `foreign_weighted_persistence_5` | 930448 | 171952 | -1.000000 | -1.000000 | -0.742047 | 0.000000 | 0.537031 | 1.000000 | 1.000000 |
| `foreign_weighted_persistence_20` | 870581 | 231819 | -1.000000 | -1.000000 | -0.532183 | 0.000000 | 0.360162 | 1.000000 | 1.000000 |
| `foreign_signed_streak_10` | 1101832 | 568 | -1.000000 | -1.000000 | -0.100000 | 0.000000 | 0.100000 | 0.900000 | 1.000000 |
| `foreign_flow_acceleration_5_20` | 870581 | 231819 | -5416.354516 | -1.253865 | -0.033546 | 0.000000 | 0.037954 | 1.310311 | 3985.835971 |
| `foreign_flow_price_divergence_5` | 346420 | 755980 | -0.996610 | -0.855767 | -0.242241 | 0.012392 | 0.254429 | 0.791090 | 0.995633 |
| `foreign_flow_price_divergence_20` | 336691 | 765709 | -0.995902 | -0.838076 | -0.243630 | 0.014736 | 0.262475 | 0.773653 | 0.995633 |

## Shock outlier audit

Counts are `abs(value) > threshold`:

| Feature | >1 | >2 | >5 | >10 | >20 |
|---|---:|---:|---:|---:|---:|
| `foreign_flow_shock_1` | 28,593 | 12,607 | 4,809 | 2,458 | 1,301 |
| `foreign_flow_shock_mean_5` | 23,476 | 11,041 | 4,427 | 2,244 | 1,225 |
| `foreign_flow_shock_mean_20` | 19,905 | 9,174 | 3,596 | 2,052 | 1,231 |

Top 20 absolute observations for each shock feature are retained below as a
data-quality diagnostic only; these are not outcome or performance analyses.

### `foreign_flow_shock_1`

| Ticker | Flow-through session | Value |
|---|---|---:|
| FUJI | 2022-12-20 | 62062.306900 |
| CASA | 2021-10-12 | -41719.091451 |
| JGLE | 2024-05-02 | -31310.149055 |
| CASA | 2021-10-13 | -21154.876754 |
| PSKT | 2022-01-18 | -19722.120000 |
| PSKT | 2022-01-11 | -19438.888485 |
| FUJI | 2022-12-21 | 14337.621009 |
| PSKT | 2022-01-14 | -14206.242791 |
| FUJI | 2024-01-05 | -13926.887771 |
| PSKT | 2022-01-13 | -10612.604651 |
| PSKT | 2022-01-12 | -6123.900606 |
| ASMI | 2023-10-20 | -4614.212121 |
| TGRA | 2023-12-18 | 4528.500000 |
| JGLE | 2024-05-03 | -4335.047532 |
| PSKT | 2022-01-07 | -4203.870968 |
| TURI | 2021-10-26 | 3818.003649 |
| NIRO | 2025-06-30 | -3311.491935 |
| PSKT | 2022-01-17 | -3139.965385 |
| KREN | 2023-09-13 | 2836.666667 |
| TARA | 2022-01-06 | -2828.896210 |

### `foreign_flow_shock_mean_5`

| Ticker | Flow-through session | Value |
|---|---|---:|
| FUJI | 2022-12-23 | 15786.679712 |
| FUJI | 2022-12-26 | 15279.264739 |
| CASA | 2021-10-18 | -13038.816181 |
| PSKT | 2022-01-18 | -10760.966687 |
| PSKT | 2022-01-17 | -10704.320383 |
| PSKT | 2022-01-14 | -10499.076397 |
| PSKT | 2022-01-19 | -9536.189379 |
| PSKT | 2022-01-13 | -8498.602305 |
| PSKT | 2022-01-20 | -7413.707598 |
| JGLE | 2024-05-08 | -7238.053429 |
| JGLE | 2024-05-03 | -7177.781539 |
| JGLE | 2024-05-06 | -7170.103294 |
| JGLE | 2024-05-07 | -7158.037481 |
| PSKT | 2022-01-12 | -6376.081102 |
| JGLE | 2024-05-02 | -6310.772033 |
| PSKT | 2022-01-11 | -5182.308981 |
| CASA | 2021-10-19 | -4694.997891 |
| PSKT | 2022-01-21 | -4572.473122 |
| PSKT | 2022-01-24 | -3944.538621 |
| FUJI | 2022-12-27 | 2866.804999 |

### `foreign_flow_shock_mean_20`

| Ticker | Flow-through session | Value |
|---|---|---:|
| PSKT | 2022-02-02 | -3985.855287 |
| PSKT | 2022-01-31 | -3985.851440 |
| PSKT | 2022-01-28 | -3985.850346 |
| PSKT | 2022-01-27 | -3985.849579 |
| PSKT | 2022-02-04 | -3978.115178 |
| PSKT | 2022-02-03 | -3978.113109 |
| FUJI | 2023-01-13 | 3946.175481 |
| FUJI | 2023-01-16 | 3819.472581 |
| PSKT | 2022-02-07 | -3767.930645 |
| PSKT | 2022-02-08 | -3662.326690 |
| CASA | 2021-11-09 | -3259.703504 |
| PSKT | 2022-02-09 | -2690.652106 |
| PSKT | 2022-02-10 | -2384.565013 |
| PSKT | 2022-02-11 | -1853.980714 |
| JGLE | 2024-05-29 | -1840.865413 |
| JGLE | 2024-05-30 | -1840.865413 |
| JGLE | 2024-06-03 | -1840.865413 |
| JGLE | 2024-05-31 | -1840.865413 |
| JGLE | 2024-05-28 | -1840.863879 |
| JGLE | 2024-05-27 | -1840.829138 |

The repeated FUJI/CASA/JGLE/PSKT clusters are retained as unresolved data
quality observations for independent review. They are not clipped, winsorized,
removed, or reinterpreted in this lane.

## Percentile behavior

For `foreign_flow_shock_percentile_120` (`n=899,158`):

| Bin | Count |
|---|---:|
| 0.0–0.1 | 93,155 |
| 0.1–0.2 | 68,740 |
| 0.2–0.3 | 58,594 |
| 0.3–0.4 | 53,719 |
| 0.4–0.5 | 184,355 |
| 0.5–0.6 | 169,295 |
| 0.6–0.7 | 61,929 |
| 0.7–0.8 | 56,880 |
| 0.8–0.9 | 66,680 |
| 0.9–1.0 | 85,811 |

Exact zero rate is **1.0768%**; exact one rate is **1.0306%**. Median is
**0.5000**, with Q25 **0.3083** and Q75 **0.6750**. The percentile does not
collapse to only the endpoints.

## Cross-sectional rank behavior

The following counts are finite rank observations per source session; the
final calendar session has no next feature session and therefore contributes
zero output ranks.

| Feature | Min/session | Median/session | Max/session | Sessions >=50 | >=100 | >=200 | Constant/collapsed sessions | Range [0,1] |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `xs_rank_foreign_flow_shock_1` | 0 | 267 | 433 | 1,240 | 1,240 | 1,240 | 0 | PASS |
| `xs_rank_foreign_flow_shock_mean_5` | 0 | 266 | 432 | 1,240 | 1,240 | 1,240 | 0 | PASS |
| `xs_rank_foreign_flow_shock_mean_20` | 0 | 260 | 421 | 1,230 | 1,230 | 1,230 | 0 | PASS |

Rank finite-value distributions are centered near 0.5 and show no constant
source session.

## Persistence and streak behavior

| Feature | Exact -1 | Exact 0 | Exact +1 | P01 | Q25 | Median | Q75 | P99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `foreign_weighted_persistence_5` | 16.2959% | 19.4476% | 11.7667% | -1.0000 | -0.7420 | 0.0000 | 0.5370 | 1.0000 |
| `foreign_weighted_persistence_20` | 6.5726% | 9.1357% | 4.9861% | -1.0000 | -0.5322 | 0.0000 | 0.3602 | 1.0000 |
| `foreign_signed_streak_10` | 2.1922% | 42.7000% | 0.9866% | -1.0000 | -0.1000 | 0.0000 | 0.1000 | 0.9000 |

Persistence is not concentrated only at zero or both endpoints. Streak has a
large but interpretable zero mass and much smaller exact endpoint masses.

## Complete missingness audit

| Feature | Missing | Warm-up | Not-primary/not-applicable | Source-data/invalid | Warm-up threshold |
|---|---:|---:|---:|---:|---:|
| `foreign_participation_1` | 121291 | 0 | 0 | 121291 | 0 |
| `foreign_participation_mean_5` | 159884 | 2916 | 0 | 156968 | 4 |
| `foreign_flow_shock_1` | 138429 | 7290 | 0 | 131139 | 10 |
| `foreign_flow_shock_mean_5` | 171952 | 10207 | 0 | 161745 | 14 |
| `foreign_flow_shock_mean_20` | 231819 | 21186 | 0 | 210633 | 29 |
| `foreign_flow_shock_percentile_120` | 203242 | 51469 | 0 | 151773 | 70 |
| `xs_rank_foreign_flow_shock_1` | 754563 | 0 | 753931 | 632 | 10 |
| `xs_rank_foreign_flow_shock_mean_5` | 755980 | 0 | 753931 | 2049 | 14 |
| `xs_rank_foreign_flow_shock_mean_20` | 765709 | 2303 | 753931 | 9475 | 29 |
| `foreign_weighted_persistence_5` | 171952 | 10207 | 0 | 161745 | 14 |
| `foreign_weighted_persistence_20` | 231819 | 21186 | 0 | 210633 | 29 |
| `foreign_signed_streak_10` | 568 | 0 | 0 | 568 | 0 |
| `foreign_flow_acceleration_5_20` | 231819 | 21186 | 0 | 210633 | 29 |
| `foreign_flow_price_divergence_5` | 755980 | 0 | 753931 | 2049 | 14 |
| `foreign_flow_price_divergence_20` | 765709 | 2303 | 753931 | 9475 | 29 |

## Primary-liquid parity audit

The accepted clean-V2 prepared table
`pit_safe_ranking_v2_prepared_model_table.parquet` is available and hash-pinned
by its parent artifact manifest:

`b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`

It contains `292,631` model-support rows, `737` tickers, and the date range
`2021-06-02` through `2026-07-17`. It has a `universe_primary_liquid` column,
but every row in that table is already primary-liquid; it is not a
full-universe state artifact.

As a bounded keyed overlap check, all **292,631/292,631** prepared rows matched
the reconstructed context and had **0 mismatches**. This does not establish
full-universe parity because the prepared table contains no non-primary rows
against which to compare the reconstructed exclusion boundary.

No accepted authoritative full-universe `universe_primary_liquid` artifact was
located in the repository or the external clean-V2 artifact lineage. The
full-universe parity question is therefore **NOT PROVABLE**, not a fabricated
PASS. The current context remains explicitly identified as a clean-V2 rule
reconstruction over the full causal panel.

## Validation and decision boundary

- source/output artifacts: read-only; unchanged;
- no provider calls, model fit/scoring, or outcome/label access;
- formula and V2 feature contract: unchanged;
- checkpoint status: `REVIEW`;
- no alpha experiment is started by this audit.

The artifact behavior is broadly interpretable: ranks have healthy spread,
percentile is not endpoint-collapsed, persistence/streak have meaningful
interior mass, and missingness is explicitly partitioned. However, the
repeated large-shock clusters and absence of a full-universe authoritative
primary-flag artifact remain review findings. This checkpoint records evidence
for ChatGPT's acceptance decision; it does not declare
`FOREIGN_FLOW_REPRESENTATION_V2_CENSUS_ACCEPTED`.

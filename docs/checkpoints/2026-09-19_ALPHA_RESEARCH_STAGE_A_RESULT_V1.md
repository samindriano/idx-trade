# Alpha Research Program — Stage A Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Protocol: `2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1`
Stage: `A_OUTCOME_BLIND`
Result: `STRUCTURAL_CAPABILITY_ONLY`

## Scope and safety

This run read only the two locally staged research artifacts named in the
protocol. It did not read historical targets, forward labels, prospective
outcomes, counters, provider endpoints, capture/runtime state, or cloud/R2.
No incumbent or canonical artifact was modified.

The source admission result remains `NO-GO` for new-alpha historical outcome
claims. Therefore none of the numbers below is an IC, OOS, performance, or
"better alpha" claim.

## Reproducibility

- Code: `research/alpha_stage_a_v1.py`
- Code SHA-256: `3a5f018663a4a7848d19daec15a882523027ca4c1ad6cb719911c8c9a41dbc54`
- External staging directory:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a\20260919T\`
- Feature parquet SHA-256:
  `074b1a84c73eb139348d2999416cc2904e0a20b3544c329ca780ff7e2b497169`
- Audit JSON SHA-256:
  `7f0dcaa8ad581881a82080ad812b2bc9049be37f2d8aa5cd12e89f106869cbb8`
- Manifest SHA-256:
  `c89588ccd7ab5b9e4159221709f49fd2470961f43d6ab61c9331bf57eb958dc9`
- Panel source SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Financial source SHA-256:
  `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b`

## Structural checks

- Input/derived rows: 981,940.
- Unique tickers: 945.
- Date range: 2021-04-29 through 2026-07-31.
- Duplicate `(ticker,date)` rows: 0.
- Non-null ticker/date rows: 981,940 / 981,940.
- Outcome-named columns in derived artifact: none.
- Top-10 ticker row share: 1.2832%.
- Top-10 date row share: 0.8789%.
- Financial join rows with a finite C3 score: 34,412.

## Candidate construction results

| ID | Finite rows | Coverage | Dates | Tickers | Stage A status |
|---|---:|---:|---:|---:|---|
| C1 `residual_reversal_5_v1` | 889,625 | 90.5987% | 1,199 | 932 | PASS — capability only |
| C2 `participation_confirmation_5_v1` | 926,482 | 94.3522% | 1,201 | 937 | PASS — capability only |
| C3 `financial_quality_growth_v1` | 34,412 | 3.5045% | 291 | 274 | BLOCKED — partial source/low coverage |
| C4 `path_efficiency_reversal_20_v1` | 926,225 | 94.3260% | 1,240 | 932 | PASS — capability only |

Finite date ranges were 2021-08-02–2026-07-31 (C1), 2021-07-29–2026-07-31
(C2), 2025-04-25–2026-07-17 (C3), and 2021-06-03–2026-07-31 (C4).

## Internal overlap

Spearman correlations on the common finite rows were:

| Pair | Spearman |
|---|---:|
| C1 / C2 | -0.33912302 |
| C1 / C3 | -0.02141449 |
| C1 / C4 | 0.46224266 |
| C2 / C3 | -0.04513157 |
| C2 / C4 | -0.18524050 |
| C3 / C4 | -0.02294429 |

These are feature-to-feature diagnostics only. Incumbent overlap/correlation
was not opened from monitoring/prospective score artifacts because the current
source-admission gate does not authorize a new-alpha comparison. Therefore
orthogonality to V4-X1 is `UNKNOWN`, not inferred from these pairwise values.

## Candidate disposition

- C1, C2, and C4 are retained as `FUTURE_RESEARCH` capability candidates,
  not alpha survivors. Their causal formulas materialized with broad panel
  coverage, but the panel is frozen-only for new alpha claims.
- C3 is `BLOCKED`: its source is partial/parked and its all-five-field
  complete/provenance-valid coverage is only 3.5045%. No partial-bundle or
  threshold rescue is allowed.
- No candidate received target access, IC/ICIR, fold results, economics,
  robustness pass, or `RESEARCH_SURVIVOR` status.

## Next legal step

Stop the current historical alpha search. A future lane may perform a new
read-only data-admission review if an authoritative same-science,
population-wide, historical-as-of source contract becomes available. Until
then the exact blocker is source admission, not a failed alpha result.

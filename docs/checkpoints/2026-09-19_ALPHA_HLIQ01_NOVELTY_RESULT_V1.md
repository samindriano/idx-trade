# H-LIQ-01 Novelty Diagnostic V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `G_J_HLIQ01_TURNOVER_LEVEL_NOVELTY_DIAGNOSTIC`
Result: `PASS_STRUCTURAL_ONLY / NOVELTY_PENDING`

## Question

Is H-LIQ-01's rolling variability of `log(close * volume)` merely a
transformation of C2's turnover-level component, or does it carry a distinct
temporal-variability structure?

This is a target-free diagnostic over the frozen final 600 sessions
(`2024-01-12`–`2026-07-31`). It does not create C5, tune a formula, access
outcomes, or authorize future evaluation.

## Results

| Reference | Mean daily Spearman vs H-LIQ | Mean Top-30 overlap |
|---|---:|---:|
| C1 | -0.0453 | 8.97% |
| C2 | 0.0996 | 31.34% |
| C4 | -0.1050 | 12.48% |
| C2 turnover-level component alone | 0.1648 | 39.40% |

The turnover-level component has materially more relationship with H-LIQ than
the full C2 score, but the relationship is still far from identity. This is
consistent with H-LIQ measuring temporal variability rather than simply the
current abnormal-turnover level.

## Conditional dependence

Mean daily Spearman by same-day market-value quartile:

| Value bucket | H-LIQ vs turnover level | H-LIQ vs C2 |
|---|---:|---:|
| Q1 bottom value | -0.0460 | 0.0449 |
| Q2 | 0.2554 | 0.0319 |
| Q3 | 0.3655 | 0.0998 |
| Q4 top value | 0.4678 | 0.1958 |

The mechanism is most distinct among lower-value names and shows structurally
higher participation dependence among higher-value names. This resolves the
narrow novelty question only partially: H-LIQ is not a monotone duplicate of
C2, but the Q4 relationship is a structural dependence signal; its economic
meaning, capacity, and PIT safety remain unknown.

## Decision

Retain H-LIQ-01 as:

`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`

Do not create candidate `C5`. The remaining blockers are bottom-value
concentration, capacity/friction realism, sector history, unresolved
corporate-action/PIT authority, and lack of protected target admission. No
parameter sweep or target-based selection is justified by this diagnostic.

## Artifacts and hashes

- Builder: `research/alpha_hliq01_novelty_diagnostic_v1.py`
- Builder SHA-256: `ec8642d63ca82aa177dd0ef200c821e763f6eba201642e59e0944d607dedfbe7`
- Verifier: `research/verify_alpha_hliq01_novelty_diagnostic_v1.py`
- Verifier SHA-256: `4b1ba07d4d1d8c7de66616b59e3050ab54c9118aed46ad7f49442f22d2d9b6b3`
- Output: `alpha_hliq01_novelty_diagnostic_v1.json` in
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`
- Output SHA-256: `83869c995fdfc1fbe0449ad61093fa6c6f205721a38df191100045f176e2594b`
- Verifier result: `PASS`
- Target/provider/outcome access: none
- Candidate ID created: `false`

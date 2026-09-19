# Structural Orthogonality Map V1

Target-free, incumbent-free internal rank diagnostics. These are not
incremental-alpha or predictive comparisons.

| Pair | Spearman |
|---|---:|
| C1 / C2 | -0.23035511 |
| C1 / C3 | -0.02365537 |
| C1 / C4 | 0.41126169 |
| C2 / C3 | -0.04554962 |
| C2 / C4 | -0.11908659 |
| C3 / C4 | -0.03261201 |

Interpretation: C1/C4 require duplicate-mechanism review; C3 is internally
distinct but sparse; C2 is not a simple duplicate of C1/C4 in this diagnostic.
Incumbent overlap, conditional information, and target-ranked overlap remain
`UNKNOWN/BLOCKED`.

Extended daily/rolling map: `2026-09-19_ALPHA_STRUCTURAL_LAB_RESULT_V1.md`.
The extended result shows C1/C4 mean daily Spearman `0.4624`, Top-30 overlap
`34.89%`, and Top-30 Jaccard `21.57%`; C1/C2 are `-0.2454` / `12.21%` /
`6.77%`; C2/C4 are `-0.1494` / `11.00%` / `6.03%`. These remain structural
dependence diagnostics, not predictive orthogonality.

Combination-readiness extension: `2026-09-19_ALPHA_COMBINATION_ECONOMICS_RESULT_V1.md`.
Equal-weight C1+C4 has the lowest combination turnover among the tested
combinations (`34.85%`) and retains mean Top-30 overlap of `63.29%` with C1
and `59.86%` with C4. C1+C2, C2+C4, and C1+C2+C4 materially alter the selected
set, especially relative to C2. These are future combination hypotheses only;
no ensemble weight was optimized and no candidate ID was created.

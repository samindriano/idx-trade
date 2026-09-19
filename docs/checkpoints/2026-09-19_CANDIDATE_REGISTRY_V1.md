# Candidate Registry V1

| ID | Candidate | Coverage | Structural status | Historical status | Current disposition |
|---|---|---:|---|---|---|
| C1 | `residual_reversal_5_v1` | 95.0065% | Top-30 turnover 42.15%; burden 25.29 bps | blocked by admission | `FUTURE_RESEARCH` |
| C2 | `participation_confirmation_5_v1` | 100.0000% | turnover 32.91%; burden 19.75 bps | blocked by admission | `FUTURE_RESEARCH` |
| C3 | `financial_quality_growth_v1` | 9.9736% | 278 Top-30 dates; Top-10 share 25.77% | blocked by partial PIT/admission | `BLOCKED` |
| C4 | `path_efficiency_reversal_20_v1` | 99.8591% | turnover 23.70%; burden 14.22 bps | blocked by admission | `FUTURE_RESEARCH` |

No candidate is a `RESEARCH_SURVIVOR`. No new candidate was added; the budget
remains exactly C1–C4.

## Structural lab refinement

- C1: `FUTURE_RESEARCH / MODERATE`; broad coverage, high churn, heavy raw-score
  tails, and a mild low-liquidity tilt.
- C2: `FUTURE_RESEARCH / MODERATE`; full coverage and lower churn than C1, but
  very heavy raw-score tails; liquidity is near-neutral.
- C3: `BLOCKED / FRAGILE`; sparse/late PIT support and concentration dominate
  its otherwise strong persistence.
- C4: `FUTURE_RESEARCH / MODERATE`; lowest broad-candidate churn, but strongest
  low-liquidity tilt and substantial structural overlap with C1.

Source: `2026-09-19_ALPHA_STRUCTURAL_LAB_RESULT_V1.md`. These labels are
structural only and do not rank expected alpha.

## Structural robustness battery

`2026-09-19_ALPHA_STRUCTURAL_ROBUSTNESS_RESULT_V1.md` adds a target-free
robustness gate. Monotone rank/z-score/robust-z transforms are exact Top-30
duplicates and are not separate candidates. C1/C2/C4 retain 600 usable Top-30
dates under deterministic 5% score masking with 94.88%–95.17% mean overlap;
C3 remains support-fragile. Horizon variants materially change Top-30 sets and
remain unregistered representation questions, not candidate IDs.

The literature/mechanism card pack (`2026-09-19_ALPHA_HYPOTHESIS_CARD_PACK_V1.md`)
records one potential new temporal-liquidity direction, H-LIQ-01, as
`NOVELTY_PENDING / ECONOMIC_CAUTION`; its fixed prototype is documented in
`2026-09-19_ALPHA_HLIQ01_STRUCTURAL_RESULT_V1.md`, but it is not admitted as
C5. Intraday reversal,
financial change/disagreement, and flow-event directions remain
source/capability blocked, while high-participation reversal remains a
non-novel retry risk.

The H-LIQ-01 adversarial audit is in
`2026-09-19_ALPHA_HLIQ01_ROBUSTNESS_RESULT_V1.md`; its status remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION` because conditional C2
dependence, horizon sensitivity, listing-age concentration, and missing sector
data remain unresolved.

C3 contract mapping (`2026-09-19_C3_FINANCIAL_CONTRACT_MAP_RESULT_V1.md`)
shows that a quality-only capability island is broader, but any YoY-containing
contract has the same sparse support as all-five. This is a capability finding,
not a C3A/C3B/C3C admission; the registry remains exactly C1–C4.

## Structural combination hypotheses

`2026-09-19_ALPHA_COMBINATION_ECONOMICS_RESULT_V1.md` evaluates exactly four
equal-weight combinations of existing rank columns. C1+C4 has the lowest
combination turnover (`34.85%`) and the most balanced component overlap in the
bounded structural test. The other combinations remain useful complementarity
questions, especially because their C2 overlap is low. These are not candidate
IDs, are not predictive evidence, and are not added to the four-candidate
protected evaluation packet.

# Eligibility versus Feature Warm-Up Audit V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_SEPARATION / NO ADMISSION`

## Question

Are candidate score gaps caused by the security-eligibility mask, by candidate
feature warm-up/availability after eligibility, or by finite scores leaking
outside the eligible decision universe?

## Result

The guarded feature artifact has 981,940 rows, 945 observed tickers, 1,260
official dates, and 310,761 rows marked `eligible_decision_universe`. Every
finite C1/C2/C3/C4 score is inside that eligibility mask; no candidate has a
finite score outside it.

| Candidate | Finite rows | Eligible missing rows | Finite outside eligibility | Median first-finite minus first-eligible days |
|---|---:|---:|---:|---:|
| C1 | 295,243 | 15,518 | 0 | 4.0 |
| C2 | 310,761 | 0 | 0 | 0.0 |
| C3 | 30,994 | 279,767 | 0 | 1,322.0 |
| C4 | 310,323 | 438 | 0 | 0.0 |

C1 has additional candidate-specific warm-up/availability after eligibility;
C4 has only a small residual; C2's score support coincides with the current
eligible rows; and C3's sparse support is overwhelmingly a feature/data
availability boundary within eligible rows, not a score leak outside eligibility.
The first-finite delay statistics are descriptive and do not identify the
underlying authority or cause.

## Interpretation

This provides a clean implementation distinction:

- security eligibility is represented by the `eligible_decision_universe` mask;
- candidate feature warm-up/availability is represented by finite score support
  within that mask;
- the current producer gates all candidate scores by the eligibility mask.

This does not decide whether the current eligibility policy is authoritative.
It also does not prove historical population completeness, PIT/report
availability, issuer/ISIN continuity, corporate-action basis, or predictive
validity. No candidate, era, policy, population, or outcome was selected.

## Reproducibility

- Script: `research/alpha_eligibility_feature_warmup_audit_v1.py`
- Test: `tests/test_alpha_eligibility_feature_warmup_audit_v1.py`
- Durable result: `research_knowledge/eligibility_feature_warmup_v1.json`
- Feature input SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Code SHA-256: `a703573c66ba05c98d2616f5e42ab2637f6f34740692d0d4fbdd078d74ee5311`
- Isolated external result SHA-256: `f5d98741ad16ed3171ec7b107d787138f83417655161e02ce2520a86aa81d481`

Protected outcomes, canonical data, provider, cloud/R2, capture, telemetry,
scheduler, production, and incumbent state remained untouched.

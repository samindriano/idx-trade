# Financial PIT Market-Wide Census Independent Acceptance

Date: 2026-08-13
Reviewed HEAD: `419f0be54a7b08ee958c52b8a727be9423286d96`

Verdict: `FINANCIAL_PIT_MARKETWIDE_FACT_CENSUS_ACCEPTED_TEMPLATE_DRIFT_AUDIT_REQUIRED_BEFORE_FEATURE_CONTRACT_FREEZE`

The offline census is accepted for its stated extraction/coverage scope. It processed all 5,965 accepted PIT-ready filings from the pinned 6,108-row source inventory and preserved the prior fail-closed admission rules.

Key review findings:
- 21,962 / 22,041 candidate facts were extracted. This is parser success over discovered candidates, not dense panel coverage.
- The remaining 64 unresolved-unit records are concentrated in ASII filings and remain excluded.
- The remaining 15 unresolved-period records are prior-period XBRL contexts and remain excluded.
- No unresolved taxonomy or same-priority conflict was observed.
- Core fact coverage is only about 40–50% of eligible filings, so missingness must remain explicit.
- The sparse exact `cash` concept must remain distinct from `cash_and_cash_equivalents` unless a later reviewed semantic contract says otherwise.

A material temporal discontinuity needs explanation before a feature contract is frozen. Candidate facts per filing are roughly 6.1–6.2 throughout 2024 and 2025 Q1, but fall to roughly 1.4–1.8 for 2025 H1, 2025 9M, 2025 FY, 2026 Q1 and 2026 H1. Because missing canonical labels are recorded as `missing_facts` rather than `UNRESOLVED_LABEL` candidate records, the 99.6416% candidate extraction rate does not rule out template/label drift. The discontinuity may reflect a genuine filing/template difference, but that has not yet been demonstrated.

Therefore the next allowed milestone is a separate bounded **missing-fact/template-drift and co-occurrence feasibility audit** over the existing immutable corpus. It should attribute the post-Q1-2025 coverage drop by template/sheet/label family and determine whether missing facts are true semantic absence or unsupported label/template variants. No guessed fuzzy mapping is allowed.

Only after that audit may a feature-contract review be frozen. That later contract must define as-of version selection, statement-scope comparability, like-period comparability, currency/unit/scale comparability, explicit missingness, semantic identities, and pairwise eligibility coverage.

No feature materialization or downstream model work is authorized by this checkpoint.

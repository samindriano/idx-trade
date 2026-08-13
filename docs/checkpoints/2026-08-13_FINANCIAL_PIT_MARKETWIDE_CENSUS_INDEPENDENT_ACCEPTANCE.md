# Financial PIT Market-Wide Census Independent Acceptance

Date: 2026-08-13
Reviewed HEAD: `419f0be54a7b08ee958c52b8a727be9423286d96`

Verdict: `FINANCIAL_PIT_MARKETWIDE_FACT_CENSUS_ACCEPTED_CONDITIONAL_GO_FOR_BOUNDED_FEATURE_CONTRACT_DESIGN`

The offline census is accepted for its stated scope. It processed all 5,965 accepted PIT-ready filings from the pinned 6,108-row source inventory and preserved the prior fail-closed admission rules.

Key review findings:
- 21,962 / 22,041 candidate facts were extracted. This is parser success over discovered candidates, not dense panel coverage.
- The remaining 64 unresolved-unit records are concentrated in ASII filings and remain excluded.
- The remaining 15 unresolved-period records are prior-period XBRL contexts and remain excluded.
- No unresolved taxonomy or same-priority conflict was observed.
- Core fact coverage is only about 40–50% of eligible filings, so missingness must remain explicit.
- The sparse exact `cash` concept must remain distinct from `cash_and_cash_equivalents` unless a later reviewed semantic contract says otherwise.

The next allowed milestone is a separate bounded feature-contract and co-occurrence-feasibility review. It must define as-of version selection, statement-scope comparability, like-period comparability, currency/unit/scale comparability, explicit missingness, semantic identities, and pairwise eligibility coverage before any feature materialization.

No downstream model work is authorized by this checkpoint.

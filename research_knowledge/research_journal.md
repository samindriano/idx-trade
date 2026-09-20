# Durable Research Journal

This journal is a compact batch log. Detailed evidence remains in the linked
checkpoint files; this file records why the next question changed.

## 2026-09-19 — structural and mechanism batch

- Reconstructed prior alpha/failure history and froze the outcome-blind C1–C4
  budget.
- Rejected the first Stage-A implementation as an engineering defect, then
  built the corrected causal/session/key implementation.
- Measured C1–C4 structural support, turnover, concentration, robustness,
  internal dependence, and proxy economics.
- Explored H-LIQ-01, H-VOL-01, H-EXC-01, and H-EXC-02 without adding C5.
- Closed monotone transforms and unsafe/raw representations as no-retry or
  future-only directions.

## 2026-09-19 late — red-team and source-capability batch

- Red-teamed CA/price basis, capacity tails, H-LIQ decomposition/persistence,
  source semantics, and packet freshness.
- Audited Dataset-Saham-IDX, Open capability, foreign-flow, lifecycle,
  ownership/free-float, market context, and panel-depth surfaces.
- Conclusion: source availability is not the same as PIT or admission authority.

## 2026-09-20 — forensic closure and tooling batch

- Audited BBCA basis/event linkage, HSC, broker/margin, LBRE, statutory
  free-float, and local-surface closure.
- Formalized the CA/issuer/basis admission contract.
- Independently replayed C1/C2/C4 constructor: 981940 keys with zero
  eligibility/score/rank mismatches.
- Formalized the eligibility contradiction and fail-closed guard.
- Hardened packet/firewall/lane controls and produced the ChatGPT audit handoff.

## 2026-09-20 — durable knowledge batch

- Added this compact machine-readable and human-readable memory layer.
- No experiment was rerun and no protected data was accessed.
- The next high-information question is eligibility provenance; if authority
  remains missing, classify `POLICY_AUTHORITY_MISSING` and move to tooling,
  common-support, and historical reinterpretation surfaces.

## Eligibility provenance addendum

- The protocol gives 60 the meaning of trailing official-session lookback and
  20 the meaning of minimum finite observations; the median threshold is part of
  the liquidity rule.
- Both Stage-A versions inherit generic `min_periods=window` behavior, so the
  current implementation requires a complete 60-value rolling window and makes
  the later `>=20` test redundant for those rows.
- Candidate feature windows also use 60/20, while `security_master` exposes a
  separate generic warm-up path. No evidence supports an incumbent-specific
  origin, and Data-QA is a separate blocked gate.
- Classification remains `POLICY_AUTHORITY_MISSING`; no population was chosen.

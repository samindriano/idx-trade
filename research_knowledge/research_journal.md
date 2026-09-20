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

## 2026-09-20 — eligibility counterfactual clarification

- Replayed the two unresolved policy interpretations outcome-blind on the
  hash-bound panel, financial bundle, official sessions, and tradability
  anchors.
- Minimum-20 produces 348,765 eligible rows versus 310,761 under minimum-60;
  the mask difference is 38,004 rows across 619 tickers.
- Common-finite rank changes are material for C1/C3/C4 (73.1086%/96.6122%/
  99.5192%) but zero for C2 because C2's feature rolling warm-up remains 60.
- This strengthens the conclusion that security eligibility and feature
  availability have been conflated in the current implementation. It does not
  establish policy authority or authorize regeneration.
- The first turnover comparison used all official dates and was superseded by
  an explicit previous-official-session calculation over the frozen 600-session
  scope; the corrected minimum-60 values align with the official structural
  scope to rounding.

## 2026-09-20 — tooling mutation and authority-packet audit

- A synthetic audit exercised corrupt hashes, missing bindings, changed code,
  network imports, obvious protected markers, C5 injection, policy selection,
  and re-entry opening. All expected failures failed closed; safe baselines
  passed.
- The audit found that the hybrid firewall is not a semantic allowlist:
  disguised field names and unexpected non-matching schema columns can pass.
- A newly surfaced data-authority packet initially passed despite five missing
  evidence refs. The verifier was corrected to require relative refs and
  counterfactual refs to exist; a dedicated missing-reference test now fails
  closed.
- The authority packet remains `BLOCKED_PRE_ADMISSION`; it is a reusable
  bounded map, not permission to open outcomes or re-enter predictive work.
- The lane verifier then exposed a separate process-scope false negative:
  legitimate `tests/` files were outside its allowlist. Adding only `tests/`
  keeps the lane narrow and removes that false failure; it does not strengthen
  runtime-access claims.

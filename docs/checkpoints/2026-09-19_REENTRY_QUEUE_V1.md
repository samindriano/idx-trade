# Re-entry Queue V1

One-shot evaluation specification: `2026-09-19_ALPHA_FUTURE_EVALUATION_PACKET_V2.md`.

V2 contract closure is independently verified in
`2026-09-19_ALPHA_REENTRY_PACKET_CONTRACT_CLOSURE_RESULT_V1.md`. The packet
remains `SPECIFICATION_ONLY / BLOCKED_BY_DATA_ADMISSION`; C3 is explicitly
fail-closed and cannot execute under the current contract.

## Conditional queue

- C1, C2, C4: engineering-ready for a future frozen comparison, pending
  authoritative data admission and common-support H5/H10 targets.
- CA-basis readiness note: under a forensic substitution of 188 unresolved
  comparison rows, C1 is materially more sensitive than C2/C4. This is not an
  alpha ranking, but C1 requires explicit price-basis resolution before it can
  be treated as equally ready for re-entry.
- CA exposure attribution update: the bounded replay exactly reproduced stored
  C1/C2/C4 scores. Direct changed rows (keys inside the 188-row artifact) versus
  spillover changed rows were C1 `66 / 82,291`, C2 `66 / 457`, and C4 `66 / 319`.
  This narrows the risk mechanism but is not causal proof or a price-basis
  admission; see `2026-09-19_ALPHA_CA_EXPOSURE_ATTRIBUTION_RESULT_V1.md`.
- C3: remains blocked until financial population coverage, knowledge time,
  period boundaries, revision/vintage, and missingness policy are certified.
- H-VOL-01: remains `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`,
  outside the protected four-ID packet. Its bounded CA stress preserves
  `99.8307%` mean and `86.6667%` minimum Top-30 overlap, but changes 547 scores
  and 8,876 ranks. Its fixed `5/20`, `5/60`, and `20/120` forms are materially
  horizon-sensitive; no C5 or re-entry status is authorized.

Structural combination hypotheses are tracked separately from the four-ID
protected packet. The equal-weight C1+C4 combination is the cleanest
structural readiness hypothesis by turnover/overlap, while C1+C2, C2+C4, and
C1+C2+C4 remain future research. None is `READY_FOR_REENTRY`, and none may be
evaluated with protected outcomes without a separately frozen packet decision.

## Required re-entry gates

1. Read fresh canonical `TEAM_STATUS.md`.
2. Verify population completeness, PIT/as-of, identity/calendar,
   corporate-action basis, revision/vintage, and both target horizons.
3. If any gate is absent, do not open outcomes and leave statuses unchanged.
4. If all gates pass, run the fixed comparison once per candidate on common
   support; no rescue, refit, or variant sweep.

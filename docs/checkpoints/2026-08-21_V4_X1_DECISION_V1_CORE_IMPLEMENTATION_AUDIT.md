# V4-X1 Decision V1 — Core Implementation + Adversarial Audit

Date: 2026-08-21 Asia/Jakarta
Status: `DECISION_V1_CORE_IMPLEMENTED_LOCAL_REVIEW_READY_NOT_HISTORICALLY_EVALUATED`

## Frozen scientific/decision contract preserved

- Alpha remains frozen `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`.
- Long-only, target 10 positions, always invested.
- New entrants must be current Top-10 consensus rank.
- Existing Top-10 is retained.
- Existing rank >20 is mandatory exit intent.
- Existing rank 11–20 is replaceable only when the best unheld Top-10 candidate is at least 5 rank positions better.
- Replacement order is deterministic: best unheld Top-10 versus worst replaceable incumbent.
- No fixed H5/H10 holding expiry.
- Decision after official EOD t; execution reference remains official Open(t+1).
- Sizing, costs, stop-loss, take-profit, market timing, foreign flow and execution fill semantics remain out of scope.

## Engineering/remediation guards implemented

1. Raw DataFrame ranking input is forbidden. Decision planning requires a `VerifiedScoreSession` produced by the manifest/artifact verifier.
2. The verifier pins clean model id, generation, model fingerprint, model-bundle fingerprint, freeze boundary, consensus formula and frozen scientific source blobs.
3. Score artifact bytes must match the manifest SHA; declared schema, row count, dates, identities, alpha range/formula, contiguous ranks and alpha/ticker rank ordering are revalidated.
4. A holding absent from the scoring artifact is only interpreted as `NO_LONGER_IN_V4_X1_DECISION_UNIVERSE` after the full upstream artifact passed verification.
5. Decision outputs are `BUY_INTENT` / `SELL_INTENT`, never fills.
6. Frozen V1 parameters are not caller-configurable; the canonical JSON has an exact SHA-256 lock.
7. Shadow state is an explicit `ShadowPortfolioState`; `REAL_PORTFOLIO` state is rejected.
8. Same-session shadow state is allowed (e.g. Open fill before EOD decision); future-session state is rejected.
9. Buys that replace mandatory exits are explicitly paired to their sell intent (`MANDATORY_EXIT_REPLACEMENT`) so the later execution layer can avoid accidental >10-position exposure after a non-fill.
10. Rank-gap replacement buy/sell intents are also symmetrically paired.
11. Tie count is carried as a diagnostic; scorer ticker tie-break semantics are verified, not redefined.

## Validation

- Focused pytest suite: 41 passed.
- `py_compile`: PASS.
- Randomized invariant test inside pytest: 10,000 cases PASS.
- Exhaustive 10-of-15 incumbent combinations: 3,003 cases PASS.

Validated invariants include:

- desired target has exactly 10 unique positions;
- no target rank >20;
- all new buys are Top-10;
- no ticker is simultaneously BUY and SELL;
- exact rank-gap boundary: 4 does not replace, 5 replaces;
- rank 20 is not a hard exit, rank 21 is;
- no eligible rank-gap replacement remains at the target fixed point;
- input row permutation does not change the plan;
- unchanged ranking at intended target is idempotent;
- shadow input is not mutated;
- all replacement peer pairs are symmetric.

## Not yet authorized / unresolved

- No historical return/PnL evaluation has been run.
- Initial historical state semantics (empty/cash start versus pre-roll) remain to be frozen before outcomes are inspected.
- Fold-boundary state carry semantics remain to be frozen before historical evaluation.
- Sizing and execution/fill/cost models remain separate later stages.

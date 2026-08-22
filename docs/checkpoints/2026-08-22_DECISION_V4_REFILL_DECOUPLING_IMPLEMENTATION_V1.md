# Decision V4 Refill Decoupling V1 — Implementation Checkpoint

Date: 2026-08-22 Asia/Jakarta

Status: `IMPLEMENTED_STATIC_REVIEW_COMPLETE_LOCAL_EXECUTION_PENDING_REPLAY_NOT_AUTHORIZED`

## Scope

This checkpoint records the implementation-only step for the preregistered Decision V4 candidate:

`V4_X1_DECISION_V4_REFILL_DECOUPLING_V1`

Branch:

`research/idx-decision-v4-refill-decoupling-implementation-v1`

Implementation + test code HEAD before this documentation commit:

`e0dc1325d92d39f9d9d58f5121b1e404bca4dd50`

Accepted preregistration HEAD:

`c3ff5ecaa930a9792047a98d6354094129ffe28f`

Controlling frozen profile:

`docs/specs/decision_v4_refill_decoupling_v1.json`

Controlling independent preregistration audit:

`docs/checkpoints/2026-08-22_DECISION_V4_REFILL_DECOUPLING_PREREGISTRATION_AUDIT_V1.md`

Audit verdict entering this step:

`PREREG_REVIEW_ACCEPTED_IMPLEMENTATION_ONLY_REPLAY_NOT_AUTHORIZED`

## Implementation

Added:

- `src/idx_trade/decision_v4_refill_decoupling.py`
- `src/idx_trade/v4_x1_decision_v4_refill_decoupling.py`
- `tests/test_decision_v4_refill_decoupling.py`
- `tests/test_v4_x1_decision_v4_refill_decoupling.py`

No existing Decision V3 implementation file was modified.

The V4 planner reuses the existing V3 data contracts, rank-session validators, challenger classifier, vacancy-fill helper, and V4-X1 verified-score projection. The incumbent classification, mandatory exits, challenger tiers, Tier-D prohibition, temporary-underfill permission, and Tier-A soft-replacement block mirror V3.

The sole preregistered behavioral divergence is:

1. classify all start-of-session incumbents using unchanged V3 semantics;
2. freeze `severe_exit_session` iff at least one start-of-session incumbent is `SEVERE_DETERIORATION_EXIT`;
3. on a flagged session, vacancy refill iterates `A_CORE` only;
4. on a non-flagged session, vacancy refill remains `A_CORE -> B_NEAR -> C_DISTANT`;
5. the session flag applies to all vacancies regardless of vacancy origin;
6. after refill, unchanged V3 Tier-A soft-replacement semantics still run;
7. remaining vacancies may stay underfilled.

No delayed-entry state, cooldown, holding-period rule, turnover cap, regime rule, Tier-D admission, threshold change, replacement-gap change, or alternative refill cap was introduced.

## Static parity review

A direct source comparison against the accepted V3 planner confirmed that the incumbent-classification block and Tier-A soft-replacement block were preserved. The new V4 branch inserts the frozen severe-session flag between incumbent classification and challenger/refill processing, and changes only the vacancy-tier iterator.

A GitHub compare from preregistration HEAD `c3ff5ecaa930a9792047a98d6354094129ffe28f` to implementation/test HEAD `e0dc1325d92d39f9d9d58f5121b1e404bca4dd50` is strictly ahead and introduces the accepted preregistration audit plus the four V4 implementation/test files; no pre-existing implementation/model/runtime file is modified by this implementation step.

## Test contract added

Focused tests are written to verify:

- bootstrap exact-Top10 parity with V3 except rule ID;
- exact non-severe-session plan parity with V3;
- severe-session B/C blocking while A refill remains allowed;
- restriction across simultaneous severe, confirmed-mild, and universe-exit vacancy origins;
- severe-session divergence from V3 confined to non-core refill permission;
- a distant challenger cannot itself create the severe-session flag;
- Tier-A soft replacement remains active and unchanged on severe sessions;
- Tier-D remains forbidden after bootstrap;
- one-session mild grace and second-consecutive mild exit remain unchanged;
- rank `>50` still exits immediately;
- V4-X1 runtime profile equals the frozen machine-readable preregistration;
- bootstrap rule ID and exact Top10 at the V4-X1 adapter;
- non-bootstrap shadow state must be bound to the V4 rule ID.

## Local execution boundary

ChatGPT performed the repository implementation and static source review. This environment did not execute the repository pytest suite.

Therefore the following remain explicitly pending local execution on the user's repository checkout:

- focused V4 tests;
- existing V3 regression tests;
- broader/full pytest;
- `git diff --check`;
- optional compile/import smoke checks.

Codex may be used only as a local command runner for those checks. It is not authorized to edit, repair, tune, or extend the implementation in that validation pass. Any failure must be reported back for ChatGPT review.

## Scientific boundary

- `600_SESSION_REPLAY_NOT_RUN = true`
- `REALIZED_DECISION_OUTCOMES_NOT_ACCESSED = true`
- `PROTECTED_FORWARD_NOT_ACCESSED = true`
- `MODEL_REFIT_OR_RESCORE = false`
- `THRESHOLD_SWEEP = false`
- `ALTERNATIVE_V4_VARIANT = false`
- `PROVIDER_OR_NETWORK_DATA_CALL = false`
- `REPLAY_AUTHORIZED = false`

The frozen source profile continues to record `replay_authorized=false`. This implementation checkpoint does not change that field and does not authorize historical replay.

## Next gate

Run the frozen implementation/test branch locally without edits. If focused/regression/full validation passes, perform a separate independent implementation/parity audit before authorizing or freezing any 600-session replay runner.

This remains the final Decision candidate. No V4.1/V4.2/rescue variant is authorized after observing future results.
